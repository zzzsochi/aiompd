import asyncio
import logging

from .protocol import Protocol
from .helpers import lock, lock_and_status
from .helpers import status_from_raw, song_from_raw
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

    def __init__(self, auto_reconnect: bool=True):
        self.auto_reconnect = auto_reconnect
        self._lock = asyncio.Lock()
        self._received_data = asyncio.Queue(maxsize=1)

    @classmethod
    @asyncio.coroutine
    def make_connection(cls, host: str='localhost', port: int=6600,
                        auto_reconnect: bool=True, loop=None):
        """ Classmethod for create the connection to mpd server.

        :param str host: hostname for connection (default `'localhost'`)
        :param int port: port for connection (default: `6600`)
        :param BaseEventLoop loop: event loop for `connect` method (default: None)
        :return: new Client instance
        """
        client = cls(auto_reconnect=auto_reconnect)
        yield from client.connect(host, port, loop)
        return client

    def _on_connection_closed(self):
        self._transport = None
        self._protocol = None
        self._status = None

    @asyncio.coroutine
    def _reconnect(self) -> asyncio.Future:
        return asyncio.ensure_future(self.connect(self._host, self._port, self._loop))

    @asyncio.coroutine
    def connect(self, host: str='localhost', port: int=6600, loop=None):
        """ Connect to mpd server.

        :param str host: hostname for connection (default `'localhost'`)
        :param int port: port for connection (default: `6600`)
        :param BaseEventLoop loop: event loop for `connect` method
            (default: `asyncio.get_event_loop()`)
        :return: pair `(transport, protocol)`
        """
        with (yield from self._lock):
            if loop is None:
                loop = asyncio.get_event_loop()

            self._host = host
            self._port = port
            self._loop = loop

            _pf = lambda: Protocol(self)  # noqa
            t, p = yield from loop.create_connection(_pf, host, port)
            self._transport = t
            self._protocol = p
            log.debug('connected to %s:%s', host, port)

            welcome = (yield from self._received_data.get())
            welcome = welcome.strip().decode('utf8')
            log.debug('welcome string %r', welcome)
            self._version = welcome.rsplit(' ', 1)[1]
            t = (int(i) for i in self._version.split('.', 2))
            self._version_tuple = Version(*t)

            return (t, p)

    @asyncio.coroutine
    def _send_command(self, command: str, *args) -> str:
        # Low-level send command to server
        args = [str(a) for a in args]
        prepared = '{}\n'.format(' '.join([command] + args))
        self._transport.write(prepared.encode('utf8'))
        log.debug('data sent: %r', prepared)
        return (yield from self._received_data.get())

    @property
    def version(self) -> str:
        return self._version

    @property
    def version_tuple(self) -> Version:
        return self._version_tuple

    @asyncio.coroutine
    def _get_status(self) -> Status:
        # Low-level get status from server, use 'get_status()' for
        raw = (yield from self._send_command('status')).decode('utf8')
        return status_from_raw(raw)

    @lock_and_status
    @asyncio.coroutine
    def get_status(self) -> Status:
        """ Get status.
        """
        return self._status

    @lock
    @asyncio.coroutine
    def current_song(self) -> Song:
        """ Return current song info.
        """
        raw = (yield from self._send_command('currentsong')).decode('utf8')
        lines = raw.split('\n')[:-2]
        parsed = dict(l.split(': ', 1) for l in lines)
        return song_from_raw(parsed)

    @lock
    @asyncio.coroutine
    def play(self, *, track: int=None, id: int=None):
        """ Play song from playlist.

        :param int track: track number
        :param int id: track id
        """
        assert track is None or id is None

        if track is not None:
            yield from self._send_command('play', track)
        elif id is not None:
            yield from self._send_command('playid', id)
        else:
            yield from self._send_command('play')

    @lock
    @asyncio.coroutine
    def stop(self):
        """ Stop.
        """
        yield from self._send_command('stop')

    @lock
    @asyncio.coroutine
    def pause(self, pause=True):
        """ Pause.
        """
        yield from self._send_command('pause', int(pause))

    @lock_and_status
    @asyncio.coroutine
    def toggle(self):
        """ Toggle play/pause.
        """
        if self._status['state'] == 'play':
            yield from self._send_command('pause', 1)
        elif self._status['state'] == 'pause':
            yield from self._send_command('pause', 0)
        elif self._status['state'] == 'stop':
            yield from self._send_command('play', 1)

    @lock_and_status
    def get_volume(self) -> int:
        """ Get current volume.
        """
        return self._status['volume']

    @lock
    @asyncio.coroutine
    def set_volume(self, value: int):
        """ Set volume.

        :param int value: volume value from 0 to 100
        """
        assert 0 <= value <= 100
        yield from self._send_command('setvol', value)

    @lock_and_status
    @asyncio.coroutine
    def incr_volume(self, value: int):
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

        yield from self._send_command('setvol', volume)

    @lock
    @asyncio.coroutine
    def next(self, count: int=1):
        """ Play next song.
        """
        yield from self._send_command('next')

    @lock
    @asyncio.coroutine
    def prev(self, count: int=1):
        """ Play previous song.
        """
        yield from self._send_command('previous')

    @lock
    @asyncio.coroutine
    def shuffle(self, start: int=None, end: int=None):
        """ Shuffle current playlist.
        """
        if start is None and end is None:
            yield from self._send_command('shuffle')
        elif start is not None and end is not None:
            yield from self._send_command('shuffle', '{}:{}'.format(start, end))
        elif end is not None:
            yield from self._send_command('shuffle', '0:{}'.format(end))
        elif start is not None:
            raise ValueError("can't set 'start' argument without 'end'")

    @lock
    @asyncio.coroutine
    def clear(self):
        """ Clear current playlist.
        """
        yield from self._send_command('clear')

    @lock
    @asyncio.coroutine
    def add(self, uri: str) -> str:
        """ Add song to playlist.
        """
        return (yield from self._send_command('add', uri))

    @lock
    @asyncio.coroutine
    def delete(self, *, id: int=None, pos: int=None) -> str:
        """ Delete song from playlist.
        """
        assert id is None or pos is None

        if id is not None:
            return (yield from self._send_command('deleteid', id))
        elif pos is not None:
            return (yield from self._send_command('delete', pos))
        else:
            raise TypeError("id or pos argument is required")

    @lock
    @asyncio.coroutine
    def playlist(self) -> list:
        raw = yield from self._send_command('playlistinfo')
        lines = raw.decode('utf8').split('\n')

        res = []
        current = None

        for line in lines:
            if line == 'OK':
                if current:
                    res.append(song_from_raw(current))

                break

            key, value = line.split(': ', 1)

            if key == 'file':
                if current:
                    res.append(song_from_raw(current))

                current = {'file': value}

            current[key] = value

        else:
            return RuntimeError("bad and in response: {!r}".format(raw))

        return res
