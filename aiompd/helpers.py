import asyncio
import logging
from types import GeneratorType

log = logging.getLogger(__name__)


def lock(func):
    # lock clinet method
    def wrapper(self, *args, **kwargs):
        if self._transport is None:
            log.error("connection closed")
            raise RuntimeError("connection closed")

        with (yield from self._lock):
            return (yield from (func(self, *args, **kwargs)))

    return wrapper


def lock_and_status(func):
    # lock, get status from server and run method
    @asyncio.coroutine
    def wrapper(self, *args, **kwargs):
        if self._transport is None:
            log.error("connection closed")
            raise RuntimeError("connection closed")

        with (yield from self._lock):
            self._status = yield from self._get_status()

            res = func(self, *args, **kwargs)
            if isinstance(res, GeneratorType):
                return (yield from res)
            else:
                return res

    return wrapper


str_bool = lambda v: v != '0'
