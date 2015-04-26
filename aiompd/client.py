import asyncio
import logging

from .protocol import Protocol
from .helpers import lock, lock_and_status, str_bool

log = logging.getLogger(__name__)

mpc_subprocesslocker = asyncio.Lock()


class Client:
    """ Client for music player daemon

    :param bool auto_reconnect: resonnect after disconect instantly
        (default `True`)
    """
    _status_casts = {
        'volume': int,
        'repeat': str_bool,
        'random': str_bool,
        'single': str_bool,
        'consume': str_bool,
        'playlist': int,
        'playlistlength': int,
        'song': int,
        'songid': int,
        'nextsong': int,
        'nextsongid': int,
        'duration': int,
        'xfade': int,
        'updating_db': int,
    }

    _transport = None
    _protocol = None
    _status = None
    auto_reconnect = True

    def __init__(self, auto_reconnect=True):
        self.auto_reconnect = auto_reconnect
        self._lock = asyncio.Lock()
        self._received_data = asyncio.Queue(maxsize=1)

    @classmethod
    @asyncio.coroutine
    def make_connection(cls, host='localhost', port=6600,
                        auto_reconnect=True, loop=None):
        """ Classmethod for create the connection to mpd server

        :param str host: hostname for connection (default `'localhost'`)
        :param int port: port for connection (default: `6600`)
        :param BaseEventLoop loop: event loop for `connect` method (default: None)
        :return: new Client instance
        """
        client = cls()
        yield from client.connect(host, port, loop)
        return client

    def _on_connection_closed(self):
        self._transport = None
        self._protocol = None
        self._status = None

    @asyncio.coroutine
    def _reconnect(self):
        return asyncio.async(self.connect(self._host, self._port, self._loop))

    @asyncio.coroutine
    def connect(self, host='localhost', port=6600, loop=None):
        """ Connect to mpd server

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

            _pf = lambda: Protocol(self)
            t, p = yield from loop.create_connection(_pf, host, port)
            self._transport = t
            self._protocol = p
            log.debug('connected to {}:{}'.format(host, port))

            yield from self._received_data.get()
            return (t, p)

    @asyncio.coroutine
    def _send_command(self, command, *args):
        # Low-level send command to server
        args = [str(a) for a in args]
        prepared = '{}\n'.format(' '.join([command] + args))
        self._transport.write(prepared.encode('utf8'))
        log.debug('data sent: {!r}'.format(prepared))
        resp = yield from self._received_data.get()
        return resp

    @asyncio.coroutine
    def _get_status(self):
        # Low-level get status from server, use 'get_status()' for
        raw = (yield from self._send_command('status')).decode('utf8')
        # lines = raw.split('\n')[:-2]
        # parsed = dict(l.split(': ', 1) for l in lines)
        # return {k: self._status_casts.get(k, str)(v) for k, v in parsed.items()}
        return {k: self._status_casts.get(k, str)(v) for k, v in
                (l.split(': ', 1) for l in raw.split('\n')[:-2])}

    @lock_and_status
    @asyncio.coroutine
    def get_status(self):
        """ Get status
        """
        return self._status

    @lock
    @asyncio.coroutine
    def play(self, track=None, id=None):
        """ Play song from playlist

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
        """ Stop
        """
        yield from self._send_command('stop')

    @lock
    @asyncio.coroutine
    def pause(self, pause=True):
        """ Pause
        """
        yield from self._send_command('pause', int(pause))

    @lock_and_status
    @asyncio.coroutine
    def toggle(self):
        """ Toggle play/pause
        """
        if self._status['state'] == 'play':
            yield from self._send_command('pause', 1)
        elif self._status['state'] == 'pause':
            yield from self._send_command('pause', 0)
        elif self._status['state'] == 'stop':
            yield from self._send_command('play', 1)

    @lock_and_status
    def get_volume(self):
        """ Get current volume
        """
        return self._status['volume']

    @lock
    @asyncio.coroutine
    def set_volume(self, value):
        """ Set volume

        :param int value: volume value from 0 to 100
        """
        assert 0 <= value <= 100
        yield from self._send_command('setvol', value)

    @lock_and_status
    @asyncio.coroutine
    def incr_volume(self, value):
        """ Change volume

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
    def next(self, count=1):
        """ Play next song
        """
        yield from self._send_command('next')

    @lock
    @asyncio.coroutine
    def prev(self, count=1):
        """ Play previous song
        """
        yield from self._send_command('previous')

    @lock
    @asyncio.coroutine
    def shuffle(self, start=None, end=None):
        """ Shuffle current playlist
        """
        assert start is None and end is None
        assert start is not None and end is not None

        if start is not None:
            yield from self._send_command('shuffle', '{}:{}'.format(start, end))
        else:
            yield from self._send_command('shuffle')

    @lock
    @asyncio.coroutine
    def clear(self):
        """ Clear current playlist
        """
        yield from self._send_command('clear')

    @lock
    @asyncio.coroutine
    def add(self, uri):
        """ Add sond to playlist
        """
        yield from self._send_command('add', uri)

    @lock
    @asyncio.coroutine
    def playlist(self):
        raw = yield from self._send_command('playlistinfo')
        lines = raw.decode('utf8').split('\n')

        res = []

        for line in lines:
            if line == 'OK':
                break

            key, value = line.split(': ', 1)
            key = key.lower()

            if key == 'file':
                res.append({key: value})
            elif key in ['pos', 'id']:
                value = int(value)

            res[-1][key] = value

        return res
