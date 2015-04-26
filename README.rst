============================================
MPD (Music Player Daemon) client for asyncio
============================================

Usage example:

.. code:: python

    import asyncio
    import aiompd

    URLS = [
        "http://mega5.fast-serv.com:8134",
        "http://176.31.240.114:8326",
        "http://74.86.186.4:10042",
        "http://s14.myradiostream.com:4668",
    ]
    PLAY_TIME = 10


    @asyncio.coroutine
    def nexter(mpc):
        yield from mpc.clear()

        for url in URLS:
            yield from mpc.add(url)

        for n in range(len(URLS)):
            yield from mpc.play(track=n)
            yield from asyncio.sleep(PLAY_TIME)


    @asyncio.coroutine
    def volumer(mpc):
        timeout = (len(URLS) * PLAY_TIME) / 200

        for volume in range(0, 101, 1):
            yield from mpc.set_volume(volume)
            yield from asyncio.sleep(timeout)

        for volume in range(100, -1, -1):
            yield from mpc.set_volume(volume)
            yield from asyncio.sleep(timeout)


    def main():
        loop = asyncio.get_event_loop()
        mpc = loop.run_until_complete(aiompd.Client.make_connection())
        loop.run_until_complete(asyncio.wait([nexter(mpc), volumer(mpc)]))


    if __name__ == '__main__':
        main()
