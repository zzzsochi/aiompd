import asyncio
import logging

log = logging.getLogger(__name__)


class Protocol(asyncio.Protocol):
    def __init__(self, client):
        self.client = client

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        log.debug('connection to {}'.format(peername))
        self.transport = transport

    def data_received(self, data: bytes):
        log.debug('data received: {!r}'.format(data.decode()))
        self.client._received_data.put_nowait(data)

    def connection_lost(self, exc: Exception):
        log.debug('connection lost')
        if exc is not None:
            log.error('connection lost exc: {!r}'.format(exc))

        self.client._on_connection_closed()

        if self.client.auto_reconnect:
            log.debug('try to reconnect')
            asyncio.ensure_future(self.client._reconnect())
