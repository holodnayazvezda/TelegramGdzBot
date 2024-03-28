import sqlite3


async def get_information_from(db_name: str, tablename: str, coloumn: str, id: str = None):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    if id:
        c.execute(f'SELECT {coloumn} FROM {tablename} WHERE id=?', (id,))
    else:
        c.execute(f"SELECT {coloumn} FROM {tablename}")
    data = c.fetchall()
    c.close()
    conn.close()
    return data
