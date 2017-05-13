import asyncio
import logging

from .helpers import ExceptionQueueItem

log = logging.getLogger(__name__)


class Protocol(asyncio.Protocol):
    def __init__(self, client):
        self.client = client
        self._input_data = b""

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        log.debug('connection to {}'.format(peername))
        self.transport = transport

    def data_received(self, data: bytes):
        log.debug('data received: {!r}'.format(data.decode()))

        if not self._input_data and data.startswith(b'ACK ['):
            self.client._received_data.put_nowait(ExceptionQueueItem(data))
            self._input_data = b""

        else:
            self._input_data += data
            if (self._input_data.startswith(b"OK") and
                    self._input_data[-1] == ord('\n') or
                    self._input_data.endswith(b"OK\n")):
                self.client._received_data.put_nowait(self._input_data)
                self._input_data = b""

    def connection_lost(self, exc: Exception):
        log.debug('connection lost')
        if exc is not None:
            log.error('connection lost exc: {!r}'.format(exc))

        self.client._on_connection_closed()

        if self.client.auto_reconnect:
            log.debug('try to reconnect')
            asyncio.ensure_future(self.client._reconnect())
