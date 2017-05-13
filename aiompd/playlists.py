from .helpers import lock, songs_list_from_raw
from .types import Playlist


class Playlists:
    def __init__(self, mpc):
        self._send_command = mpc._send_command
        self._transport = mpc._transport
        self._lock = mpc._lock

    async def _get_no_lock(self, name):
        """ Get one playlist info.
        """
        raw = (await self._send_command('listplaylistinfo', name))
        return Playlist(name=name, songs=songs_list_from_raw(raw))

    @lock
    async def list(self):
        """ List all stored playlists.
        """
        raw = (await self._send_command('listplaylists')).decode('utf8')

        playlists = []
        for name in (n[10:] for n in raw.split('\n')[:-2][::2]):
            playlists.append(await self._get_no_lock(name))

        return playlists

    @lock
    async def get(self, name):
        """ Get one playlist info.
        """
        return await self._get_no_lock(name)

    @lock
    async def load(self, name):
        """ Load playlist to current queue.
        """
        await self._send_command('load', name)

    @lock
    async def save(self, name):
        """ Save current queue to playlist.
        """
        await self._send_command('save', name)

    @lock
    async def rename(self, name, new):
        """ Rename playlist.
        """
        await self._send_command('rename', name, new)

    @lock
    async def remove(self, name):
        """ Remove playlist.
        """
        await self._send_command('rm', name)

    @lock
    async def add(self, name, url):
        """ Add song to playlist.
        """
        await self._send_command('playlistadd', name, url)

    @lock
    async def delete(self, name, song_pos):
        """ Delete song from playlist.
        """
        await self._send_command('playlistdelete', name, song_pos)

    @lock
    async def clear(self, name):
        """ Clear playlist.
        """
        await self._send_command('playlistclear', name)
