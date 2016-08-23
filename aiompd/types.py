from collections import namedtuple


Version = namedtuple('Version', ['major', 'minor', 'patch'])

Status = namedtuple('Status', [
    'state', 'time', 'elapsed', 'bitrate',  # str
    'mixrampdb', 'mixrampdelay', 'audio', 'error',  # str
    'repeat', 'random', 'single', 'consume',  # bool
    'volume', 'playlist', 'playlistlength', 'song', 'songid',  # int
    'nextsong', 'nextsongid', 'duration', 'xfade', 'updating_db',  # int
])

Song = namedtuple('Song', [
    'file', 'title', 'name',  # str
    'pos', 'id',  # int
])
