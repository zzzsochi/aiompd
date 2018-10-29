============================================
MPD (Music Player Daemon) client for asyncio
============================================

Usage example:

.. code:: python

    #!/usr/bin/env python3.7

    import asyncio
    import aiompd

    URLS = [
        "http://bb24.sonixcast.com:20038/stream",
        "http://198.58.98.83:8258/stream",
    ]
    PLAY_TIME = 15


    async def nexter(mpc):
        await mpc.clear()

        for url in URLS:
            await mpc.add(url)

        for n in range(len(URLS)):
            print("Playing track", n)
            await mpc.play(track=n)
            await asyncio.sleep(PLAY_TIME)


    async def volumer(mpc):
        timeout = (len(URLS) * PLAY_TIME) / 200

        for volume in range(0, 101, 1):
            await mpc.set_volume(volume)
            await asyncio.sleep(timeout)

        for volume in range(100, -1, -1):
            await mpc.set_volume(volume)
            await asyncio.sleep(timeout)


    async def main():
        mpc = await aiompd.Client.make_connection()
        tasks = [nexter(mpc), volumer(mpc)]
        await asyncio.gather(*tasks)


    if __name__ == '__main__':
        asyncio.run(main())
