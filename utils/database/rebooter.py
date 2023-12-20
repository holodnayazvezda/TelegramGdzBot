import asyncio
import sqlite3
import os
from datetime import datetime

from utils.bot.bots_worker import reboot_daily_users_in_all_bots
from utils.pro.pro_subscription_worker import unsubscribe_users_from_pro


async def reboot_daily_users(wait_for):
    while True:
        await asyncio.sleep(wait_for)
        date = datetime.today().strftime('%H:%M')
        if date[3:] == '00':
            await unsubscribe_users_from_pro(str(datetime.now().strftime("%y-%m-%d:%H")))
        if date == '00:00':
            conn = sqlite3.connect('./data/databases/users.sqlite3')
            c = conn.cursor()
            # удалить все записи из таблицы DAILY_USERS
            c.execute('DELETE FROM DAILY_USERS')
            conn.commit()
            c.close()
            conn.close()
            conn = sqlite3.connect('./data/databases/quantity_of_requests.sqlite3')
            c = conn.cursor()
            table_names = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            for table in table_names:
                c.execute(f"DROP TABLE IF EXISTS {table[0]}")
            conn.commit()
            c.close()
            conn.close()
            await reboot_daily_users_in_all_bots()
            os.system("pip install -U g4f==0.1.9.3")
