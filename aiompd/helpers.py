import asyncio
import logging
from types import GeneratorType

from .types import Status, Song

log = logging.getLogger(__name__)


def lock(func):
    # lock clinet method
    @asyncio.coroutine
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


def _str_bool(v: str) -> bool:
    return v != '0' if v else None


def _str_int(v: str) -> int:
    return int(v) if v else None


def status_from_raw(raw: str) -> Status:
    parsed = dict(l.split(': ', 1) for l in raw.split('\n')[:-2])
    return Status(
        # str
        state=parsed.get('state'),
        time=parsed.get('time'),
        elapsed=parsed.get('elapsed'),
        bitrate=parsed.get('bitrate'),
        mixrampdb=parsed.get('mixrampdb'),
        mixrampdelay=parsed.get('mixrampdelay'),
        audio=parsed.get('audio'),
        error=parsed.get('error'),

        # bool
        repeat=_str_bool(parsed.get('repeat')),
        random=_str_bool(parsed.get('random')),
        single=_str_bool(parsed.get('single')),
        consume=_str_bool(parsed.get('consume')),

        # int
        volume=_str_int(parsed.get('volume')),
        playlist=_str_int(parsed.get('playlist')),
        playlistlength=_str_int(parsed.get('playlistlength')),
        song=_str_int(parsed.get('song')),
        songid=_str_int(parsed.get('songid')),
        nextsong=_str_int(parsed.get('nextsong')),
        nextsongid=_str_int(parsed.get('nextsongid')),
        duration=_str_int(parsed.get('duration')),
        xfade=_str_int(parsed.get('xfade')),
        updating_db=_str_int(parsed.get('updating_db')),
    )


def song_from_raw(raw: dict) -> Song:
    return Song(
        file=raw.get('file'),
        title=raw.get('Title'),
        name=raw.get('Name'),
        pos=int(raw['Pos']) if raw['Pos'] else None,
        id=int(raw['Id']) if raw['Id'] else None,
    )
