import asyncio
import sqlite3


# непосредственно данные бота
async def update_or_create_bot_data(bot_token: str, bot_dict: str, user_id: int):
    bot_id = bot_token.split(':')[0]
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    c = conn.cursor()
    c.execute(f"CREATE TABLE IF NOT EXISTS bot_{bot_id} (token TEXT, data TEXT, users TEXT, daily_users TEXT)")
    data_column_exists = c.execute(f"SELECT 1 FROM bot_{bot_id} WHERE data IS NOT NULL LIMIT 1").fetchone() \
                         is not None
    if data_column_exists:
        c.execute(f"UPDATE bot_{bot_id} SET data=?", (bot_dict,))
        c.execute(f"UPDATE bot_{bot_id} SET token=?", (bot_token,))
    else:
        c.execute(f"INSERT INTO bot_{bot_id} (token, data, users, daily_users) VALUES (?, ?, ?, ?)", (bot_token, bot_dict, user_id, user_id))
    conn.commit()
    c.close()
    conn.close()


async def write_bot_users(user_id: str, bot_id: str) -> None:
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    c = conn.cursor()
    c.execute(f"CREATE TABLE IF NOT EXISTS bot_{bot_id} (token TEXT, data TEXT, users TEXT, daily_users TEXT)")
    user_not_in_users = not c.execute(f'SELECT users FROM bot_{bot_id} WHERE users=?', (user_id,)).fetchall()
    user_not_in_daily_users = not c.execute(f'SELECT daily_users FROM bot_{bot_id} WHERE daily_users=?', (user_id,)).fetchall()
    if user_not_in_users and user_not_in_daily_users:
        c.execute(f'INSERT INTO bot_{bot_id} (users, daily_users) VALUES (?, ?)', (user_id, user_id))
    elif user_not_in_users:
        c.execute(f'INSERT INTO bot_{bot_id} (users) VALUES (?)', (user_id,))
    elif user_not_in_daily_users:
        c.execute(f'INSERT INTO bot_{bot_id} (daily_users) VALUES (?)', (user_id,))
    conn.commit()
    c.close()
    conn.close()


async def get_amount_of_users(bot_id: int) -> tuple[int, int]:
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    c = conn.cursor()
    users, daily_users = c.execute(f'SELECT COUNT(users), COUNT(daily_users) FROM bot_{bot_id}').fetchone()
    c.close()
    conn.close()
    return users, daily_users


async def reboot_daily_users(bot_id: int) -> None:
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    c = conn.cursor()
    c.execute(f'UPDATE bot_{bot_id} SET daily_users = NULL')
    conn.commit()
    c.close()
    conn.close()


def get_working_bots_tokens() -> list:
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    c = conn.cursor()
    table_names = list(map(lambda el: el[0], c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()))
    working_bots = []
    for table_name in table_names:
        token = c.execute(f'SELECT token FROM {table_name} WHERE data LIKE "%isworking___True%"').fetchone()
        if token:
            working_bots.append(token[0])
    c.close()
    conn.close()
    return working_bots


async def get_all_bots_tokens() -> list:
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    c = conn.cursor()
    table_names = list(map(lambda el: el[0], c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()))
    all_bots_tokens = []
    for table_name in table_names:
        token = c.execute(f'SELECT token FROM {table_name}').fetchone()
        if token:
            all_bots_tokens.append(token[0])
    c.close()
    conn.close()
    return all_bots_tokens


async def reboot_daily_users_in_all_bots() -> None:
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    c = conn.cursor()
    bots_ids = list(map(lambda el: el[0].split('_')[1], c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()))
    for bot_id in bots_ids:
        await reboot_daily_users(bot_id)
    c.close()
    conn.close()


async def delete_bot(bot_token: str) -> None:
    bot_id = bot_token.split(':')[0]
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    c = conn.cursor()
    c.execute(f'DROP TABLE IF EXISTS bot_{bot_id}')
    conn.commit()
    c.close()
    conn.close()

async def start_or_stop_bot(bot_token: str, isworking: bool) -> None:
    try:
        bot_id = bot_token.split(':')[0]
        conn = sqlite3.connect('./data/databases/bots.sqlite3')
        c = conn.cursor()
        bot_dict = eval(c.execute(f'SELECT data FROM bot_{bot_id}').fetchone()[0])
        bot_dict['isworking'] = isworking
        c.execute(f"UPDATE bot_{bot_id} SET data=?", (str(bot_dict),))
        conn.commit()
        c.close()
        conn.close()
    except Exception:
        pass


async def isworking(bot_token: str, user_id: int):
    try:
        bot_id = bot_token.split(':')[0]
        conn = sqlite3.connect('./data/databases/bots.sqlite3')
        c = conn.cursor()
        is_working = eval(c.execute(f'SELECT data FROM bot_{bot_id}').fetchone()[0])['isworking']
        c.close()
        conn.close()
        return is_working
    except (sqlite3.OperationalError, TypeError):
        await update_or_create_bot_data(bot_token, str({'amount_of_unauthorized_errors': 0, 'isworking': False}), user_id)
        await isworking(bot_token, user_id)


# непосредственно данные пользователей
async def update_bot_data(user_id: str, bots_dict: dict) -> None:
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    c.execute(f'UPDATE {"user" + "_" + user_id} SET bots=?', (str(bots_dict),))
    conn.commit()
    c.close()
    conn.close()


async def get_bot_data(user_id: int):
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    bots = c.execute(f'SELECT bots FROM {"user" + "_" + user_id}').fetchall()[0][0]
    try:
        bots = eval(bots)
    except Exception:
        await update_bot_data(user_id, {})
        bots = {}
    c.close()
    conn.close()
    return bots


async def get_bot_token_by_id(bot_id: int) -> str:
    conn = sqlite3.connect('./data/databases/bots.sqlite3')
    try:
        c = conn.cursor()
        bot_token = c.execute(f'SELECT token FROM bot_{bot_id}').fetchone()[0]
        c.close()
    except Exception:
        bot_token = None
    conn.close()
    return bot_token


if __name__ == '__main__':
    asyncio.run(update_or_create_bot_data('5545579241:AAFILdiP0FNyb8SSMmB1l8cTZ9n7E24VD0E',
                                          str({'amount_of_unauthorized_errors': 0, 'isworking': True}), '1071845329'))
    asyncio.run(update_or_create_bot_data('6196558028:AAF9018kclwlwHYwGU6_yGowYwyu8KjO8s0',
                                          str({'amount_of_unauthorized_errors': 0, 'isworking': True}), '1071845329'))
