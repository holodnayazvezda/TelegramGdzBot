import sqlite3

from utils.bot.bots_worker import write_bot_users
from data.config import ADMINS
from utils.bot.bots_worker import get_bot_token_by_id


async def write_bot_token_and_admin_chat_id(chat_id: int, bot_id: int) -> None:
    bot_token = await get_bot_token_by_id(bot_id)
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS ADMIN_CHAT_ID (bot_token TEXT, chat_id INTEGER)')
    if not c.execute(f'SELECT * FROM ADMIN_CHAT_ID WHERE bot_token=? AND chat_id=?', (bot_token, chat_id)).fetchall():
        c.execute(f'INSERT INTO ADMIN_CHAT_ID (bot_token, chat_id) VALUES (?, ?)', (bot_token, chat_id))
    c.close()
    conn.commit()
    conn.close()


async def get_bot_token_and_admin_chat_id():
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    data = c.execute('SELECT * FROM ADMIN_CHAT_ID').fetchall()
    c.close()
    conn.close()
    return data


async def active_now(id_of_user: str, chat_id: int, bot_id: int) -> None:
    if id_of_user in ADMINS:
        await write_bot_token_and_admin_chat_id(chat_id, bot_id)
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS DAILY_USERS (id TEXT)')
    # если в таблице DAILY_USERS в колонке id нет id_of_user, то записать его туда
    if not c.execute(f'SELECT id FROM DAILY_USERS WHERE id=?', (id_of_user,)).fetchall():
        c.execute(f'INSERT INTO DAILY_USERS (id) VALUES (?)', (id_of_user,))
    c.execute(f'CREATE TABLE IF NOT EXISTS USERS (id TEXT)')
    # если в таблице USERS в колонке id нет id_of_user, то записать его туда
    if not c.execute(f'SELECT id FROM USERS WHERE id=?', (id_of_user,)).fetchall():
        c.execute(f'INSERT INTO USERS (id) VALUES (?)', (id_of_user,))
    conn.commit()
    c.close()
    conn.close()
    await write_bot_users(id_of_user, bot_id)


async def is_new_user(user_id: int) -> bool:
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    res = c.execute(f'SELECT COUNT(id) FROM users WHERE id = {user_id}').fetchone()[0]
    c.close()
    conn.close()
    return res == 0
