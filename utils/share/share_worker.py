import sqlite3


async def save_data_id(data_name: str, id: int, db_name: str, table_name: str) -> None:
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (data_name TEXT, id INTEGER)')
    c.execute(f'INSERT INTO {table_name} VALUES (?, ?)', (data_name, id))
    conn.commit()
    conn.close()


async def get_save_data_id(data_name: str, db_name: str, table_name: str) -> tuple:
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (data_name TEXT, id INTEGER)')
    id = c.execute(f'SELECT id FROM {table_name} WHERE data_name = ?', (data_name,)).fetchone()
    conn.close()
    if id:
        return id[0], True
    return None, False


async def save_shared_data(data_name: str, data_dict: dict, db_name: str, table_name: str) -> int:
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)')
    c.execute(f'INSERT INTO {table_name} (data) VALUES (?)', (str(data_dict),))
    id = c.lastrowid
    conn.commit()
    conn.close()
    await save_data_id(data_name, id, db_name, "shared_data_ids")
    return id


async def get_shared_data(id: int, db_name: str, table_name: str) -> dict:
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)')
    data = c.execute(f'SELECT data FROM {table_name} WHERE id = ?', (id,)).fetchone()
    conn.close()
    if data:
        return eval(data[0])
