import asyncio
import logging
from typing import List, Tuple, Optional

from .protocol import Protocol
from .playlists import Playlists
from .helpers import lock, lock_and_status
from .helpers import status_from_raw, songs_list_from_raw, song_from_raw
from .helpers import ExceptionQueueItem
from .types import Status, Song, Version

log = logging.getLogger(__name__)


class Client:
    """ Client for music player daemon.

    :param bool auto_reconnect: resonnect after disconect instantly
        (default `True`)
    """
    _transport = None
    _protocol = None
    _status = None
    _version = None
    _version_tuple = None
    auto_reconnect = True

    def __init__(self, auto_reconnect: bool=True) -> None:
        self.auto_reconnect = auto_reconnect
        self._lock = asyncio.Lock()
        self._received_data = asyncio.Queue(maxsize=1)

    @classmethod
    async def make_connection(
        cls, host: str='localhost', port: int=6600,
        auto_reconnect: bool=True,
        loop: Optional[asyncio.BaseEventLoop]=None,
    ) -> 'Client':
        """ Classmethod for create the connection to mpd server.

        :param str host: hostname for connection (default `'localhost'`)
        :param int port: port for connection (default: `6600`)
        :param BaseEventLoop loop: event loop for `connect` method (default: None)
        :return: new Client instance
        """
        client = cls(auto_reconnect=auto_reconnect)
        await client.connect(host, port, loop)
        return client

    def _on_connection_closed(self):
        self._transport = None
        self._protocol = None
        self._status = None

    async def _reconnect(self) -> asyncio.Future:
        return asyncio.ensure_future(
            self.connect(self._host, self._port, self._loop))

    async def connect(self,
                      host: str='localhost',
                      port: int=6600,
                      loop=None) -> Tuple[asyncio.Transport, asyncio.Protocol]:
        """ Connect to mpd server.

        :param str host: hostname for connection (default `'localhost'`)
        :param int port: port for connection (default: `6600`)
        :param BaseEventLoop loop: event loop for `connect` method
            (default: `asyncio.get_event_loop()`)
        :return: pair `(transport, protocol)`
        """
        async with self._lock:
            if loop is None:
                loop = asyncio.get_event_loop()

            self._host = host
            self._port = port
            self._loop = loop

            _pf = lambda: Protocol(self)  # noqa
            t, p = await loop.create_connection(_pf, host, port)
            self._transport = t
            self._protocol = p
            log.debug("connected to %s:%s", host, port)

            welcome = await self._received_data.get()
            welcome = welcome.strip().decode('utf8')
            log.debug("welcome string %r", welcome)

            self._version = welcome.rsplit(' ', 1)[1]

            _vers_t = (int(i) for i in self._version.split('.', 2))
            self._version_tuple = Version(*_vers_t)

            return (t, p)

    async def _send_command(self, command: str, *args) -> bytes:
        # Low-level send command to server
        prepared = '{}\n'.format(' '.join([command] + [str(a) for a in args]))
        self._transport.write(prepared.encode('utf8'))
        log.debug("data sent: %r", prepared)

        res = await self._received_data.get()

        if isinstance(res, ExceptionQueueItem):
            raise res
        else:
            return res

    @property
    def version(self) -> str:
        return self._version

    @property
    def version_tuple(self) -> Version:
        return self._version_tuple

    async def _get_status(self) -> Status:
        # Low-level get status from server, use 'get_status()' for
        raw = (await self._send_command('status')).decode('utf8')
        return status_from_raw(raw)

    @lock_and_status
    async def get_status(self) -> Status:
        """ Get status.
        """
        return self._status

    @lock
    async def current_song(self) -> Song:
        """ Return current song info.
        """
        raw = (await self._send_command('currentsong')).decode('utf8')
        lines = raw.split('\n')[:-2]
        parsed = dict(l.split(': ', 1) for l in lines)
        return song_from_raw(parsed)

    @lock
    async def play(self, *, track: int=None, id: int=None):
        """ Play song from playlist.

        :param int track: track number
        :param int id: track id
        """
        assert track is None or id is None

        if track is not None:
            await self._send_command('play', track)
        elif id is not None:
            await self._send_command('playid', id)
        else:
            await self._send_command('play')

    @lock
    async def stop(self):
        """ Stop.
        """
        await self._send_command('stop')

    @lock
    async def pause(self, pause: bool=True):
        """ Pause.
        """
        await self._send_command('pause', int(pause))

    @lock_and_status
    async def toggle(self):
        """ Toggle play/pause.
        """
        if self._status.state == 'play':
            await self._send_command('pause', 1)
        elif self._status.state == 'pause':
            await self._send_command('pause', 0)
        elif self._status.state == 'stop':
            await self._send_command('play', 1)

    @lock_and_status
    def get_volume(self) -> int:
        """ Get current volume.
        """
        return self._status['volume']

    @lock
    async def set_volume(self, value: int):
        """ Set volume.

        :param int value: volume value from 0 to 100
        """
        assert 0 <= value <= 100
        await self._send_command('setvol', value)

    @lock_and_status
    async def incr_volume(self, value: int):
        """ Change volume.

        :param int value: increment volume value from -100 to 100
        """
        assert -100 <= value <= 100

        if value == 0:
            return

        volume = self._status['volume'] + value

        if volume < 0:
            volume = 0
        elif volume > 100:
            volume = 100

        await self._send_command('setvol', volume)

    @lock
    async def next(self, count: int=1):
        """ Play next song.
        """
        await self._send_command('next')

    @lock
    async def prev(self, count: int=1):
        """ Play previous song.
        """
        await self._send_command('previous')

    @lock
    async def shuffle(self, start: int=None, end: int=None):
        """ Shuffle current playlist.
        """
        if start is None and end is None:
            await self._send_command('shuffle')
        elif start is not None and end is not None:
            await self._send_command('shuffle', '{}:{}'.format(start, end))
        elif end is not None:
            await self._send_command('shuffle', '0:{}'.format(end))
        elif start is not None:
            raise ValueError("can't set 'start' argument without 'end'")

    @lock
    async def clear(self):
        """ Clear current playlist.
        """
        await self._send_command('clear')

    @lock
    async def add(self, uri: str):
        """ Add song to playlist.
        """
        await self._send_command('add', uri)

    @lock
    async def delete(self, *, id: int=None, pos: int=None):
        """ Delete song from playlist.
        """
        assert id is None or pos is None

        if id is not None:
            await self._send_command('deleteid', id)
        elif pos is not None:
            await self._send_command('delete', pos)
        else:
            raise TypeError("id or pos argument is required")

    @lock
    async def playlist(self) -> List[Song]:
        raw = await self._send_command('playlistinfo')
        return songs_list_from_raw(raw)

    @lock
    async def set_random(self, value: bool):
        assert type(value) == bool
        await self._send_command('random', 1 if value else 0)

    @lock
    async def set_consume(self, value: bool):
        assert type(value) == bool
        await self._send_command('consume', 1 if value else 0)

    @lock
    async def list(self, type_: str) -> List[str]:
        assert type_ in ('any', 'base', 'file', 'modified-since')
        response = await self._send_command('list', type_)
        lines = response.decode('utf-8').split('\n')
        files = [file_ for file_ in lines if file_.startswith('file: ')]
        return [file_.split(": ")[1].lstrip() for file_ in files]

    @property
    def playlists(self):
        return Playlists(self)
