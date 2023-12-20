import asyncio


def start(function, args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(function(*args))
    loop.close()
