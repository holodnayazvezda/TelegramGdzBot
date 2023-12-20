import sqlite3

from json import loads, dumps
from data.config import (LENGTH_OF_GPT3_HISTORY_FOR_USERS, LENGTH_OF_GPT3_HISTORY_FOR_PRO_USERS,
                    LENGTH_OF_GPT4_HISTORY_FOR_USERS, LENGTH_OF_GPT4_HISTORY_FOR_PRO_USERS)
from utils.database.folder_worker import get_dictionary


async def add_request_to_history(database_name: str, table_name: str, user_id: int, request_text: str, role: str):
    conn = sqlite3.connect(database_name)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (id TEXT, requests TEXT)')
    if c.execute(f'SELECT * FROM {table_name} WHERE id=?', (user_id,)).fetchone():
        data = loads(c.execute(f'SELECT requests FROM {table_name} WHERE id=?', (user_id,)).fetchone()[0])
        data.append({"role": role, "content": request_text})
        c.execute(f'UPDATE {table_name} SET requests=? WHERE id=?', (dumps(data), user_id))
    else:
        c.execute(f'INSERT INTO {table_name} (id, requests) VALUES (?, ?)',
                  (user_id, dumps([{"role": role, "content": request_text}])))
    conn.commit()
    c.close()
    conn.close()


async def get_history_of_requests(database_name: str, table_name: str, user_id: int, has_pro: bool, model: str):
    conn = sqlite3.connect(database_name)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (id TEXT, requests TEXT)')
    data = c.execute(f'SELECT requests FROM {table_name} WHERE id=?', (user_id,)).fetchone()
    if data:
        data = loads(data[0])
        if has_pro:
            if len(data) >= LENGTH_OF_GPT3_HISTORY_FOR_PRO_USERS:
                data = []
                await clear_history_of_requests("./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history", user_id)
            elif 'gpt-4' in model:
                if len(data) > LENGTH_OF_GPT4_HISTORY_FOR_PRO_USERS:
                    data = data[-LENGTH_OF_GPT4_HISTORY_FOR_USERS:]
        else:
            if len(data) > LENGTH_OF_GPT3_HISTORY_FOR_USERS:
                data = []
                await clear_history_of_requests("./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history", user_id)
            elif 'gpt-4' in model:
                if len(data) >= LENGTH_OF_GPT4_HISTORY_FOR_USERS:
                    data = data[-LENGTH_OF_GPT4_HISTORY_FOR_USERS:]
        return data
    else:
        return []


async def clear_history_of_requests(database_name: str, table_name: str, user_id: int):
    conn = sqlite3.connect(database_name)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (id TEXT, requests TEXT)')
    c.execute(f'DELETE FROM {table_name} WHERE id=?', (user_id,))
    conn.commit()
    c.close()
    conn.close()


async def get_amount_of_referrals(user_id: int, bot_id: int, users_data: dict = None):
    if not users_data:
        users_data = await get_dictionary(str(user_id), bot_id, 1)
    if 'referral_users' in users_data:
        amount_of_referrals = len(users_data['referral_users'])
    else:
        amount_of_referrals = 0
    return amount_of_referrals


async def get_has_working_bots(user_id: int, bot_id: int, users_data: dict = None):
    if not users_data:
        users_data = await get_dictionary(str(user_id), bot_id, 1)
    if 'has_working_bots' in users_data:
        has_working_bots = users_data['has_working_bots']
    else:
        has_working_bots = False
    return has_working_bots
