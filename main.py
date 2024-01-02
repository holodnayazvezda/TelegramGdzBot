import asyncio
import subprocess
import requests
import os

from data.startup_texts import *


async def start_server(sleep_after_request: int, stop_error_count: int) -> None:
    error_count = 0
    is_working = True
    process = subprocess.Popen(['python', './handlers/super_main.py'])
    print(f'{ReshenijaBotStarted}')
    while True:
        try:
            status = requests.get("https://api.telegram.org/").status_code
        except requests.exceptions.ConnectionError:
            status = 100
        if status != 200:
            error_count += 1
            if error_count == stop_error_count:
                print(f'WARNING! The number of errors exceeded {error_count}.')
                print(f'{ReshenijaBotStoppedLowercase}')
                process.terminate()
                is_working = False
        else:
            error_count = 0
            if not is_working:
                is_working = True
                process = subprocess.Popen(['python', './handlers/super_main.py'])
                print(f'{ReshenijaBotRestarted}')
        await asyncio.sleep(sleep_after_request)


if __name__ == '__main__':
    os.system("pip install -U g4f")
    try:
        asyncio.run(start_server(3, 2))
    except KeyboardInterrupt:
        print(f'{ReshenijaBotStoppedUppercase}')
