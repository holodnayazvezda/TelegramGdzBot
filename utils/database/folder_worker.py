import sqlite3


async def create_or_dump_user(id_of_user: str, bot_id: int, users_dictionary: str, type_of_dict: int) -> None:
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    if type_of_dict == 1:
        column_name = 'data'
        c.execute(f'CREATE TABLE IF NOT EXISTS {"user" + "_" + id_of_user} (data TEXT)')
    else:
        column_name = f'data_{str(bot_id)}'
        c.execute(f'CREATE TABLE IF NOT EXISTS {"user" + "_" + id_of_user} (data TEXT, {column_name} TEXT)')
    # если в таблице data нет данных, то записать в нее users_dictionary, а если есть, то обновить
    try:
        if not c.execute(f'SELECT {column_name} FROM {"user" + "_" + id_of_user}').fetchall():
            c.execute(f'INSERT INTO {"user" + "_" + id_of_user} ({column_name}) VALUES (?)', (users_dictionary,))
        else:
            c.execute(f'UPDATE {"user" + "_" + id_of_user} SET {column_name}=?', (users_dictionary,))
    except Exception:
        c.execute(f'ALTER TABLE {"user" + "_" + id_of_user} ADD COLUMN {column_name} TEXT')
        if not c.execute(f'SELECT {column_name} FROM {"user" + "_" + id_of_user}').fetchall():
            c.execute(f'INSERT INTO {"user" + "_" + id_of_user} ({column_name}) VALUES (?)', (users_dictionary,))
        else:
            c.execute(f'UPDATE {"user" + "_" + id_of_user} SET {column_name}=?', (users_dictionary,))
    conn.commit()
    c.close()
    conn.close()


async def get_dictionary(id_of_user: str, bot_id: int, type_of_dict: int) -> dict:
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    if type_of_dict == 1:
        column_name = 'data'
        dump_data = str({'id_of_block_of_photos_send_by_bot': [], 'id_of_messages_about_bookmarks': []})
    else:
        column_name = f'data_{str(bot_id)}'
        dump_data = str({'bookmarks': {}, 'bots': {}})
    try:
        c.execute(f'SELECT {column_name} FROM {"user" + "_" + id_of_user}')
        data = c.fetchall()
    except Exception:
        await create_or_dump_user(str(id_of_user), bot_id, dump_data, type_of_dict)
        c.execute(f'SELECT {column_name} FROM {"user" + "_" + id_of_user}')
        data = c.fetchall()
    c.close()
    conn.close()
    if data:
        if data[0][0]:
            return eval(data[0][0])
        else:
            await create_or_dump_user(id_of_user, bot_id, str({'bookmarks': {}, 'bots': {}}), 1)
            await get_dictionary(id_of_user, bot_id, type_of_dict)
    else:
        return 0
