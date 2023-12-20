import asyncio
import sqlite3


async def update_bookmarks(user_id, new_dict):  # тип данных str, dict
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    try:
        data = eval(c.execute(f'SELECT data FROM {"user" + "_" + user_id}').fetchall()[0][0])
        data['bookmarks'] = new_dict
        c.execute(f'UPDATE {"user" + "_" + user_id} SET data=?', (str(data),))
    except Exception:
        c.execute(f'UPDATE {"user" + "_" + user_id} SET data=?', (str({'bookmarks': {}}),))
    conn.commit()
    c.close()
    conn.close()


async def get_dict_of_bookmarks(user_id):  # тип данных - str
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    # получить из таблицы user_id колонку bookmarks
    data = c.execute(f'SELECT data FROM {"user" + "_" + user_id}').fetchall()[0][0]
    # преобразовать строку в словарь
    try:
        bookmarks = eval(data)['bookmarks']
    except Exception:
        c.execute(f'UPDATE {"user" + "_" + user_id} SET data=?', (str({'bookmarks': {}}),))
        conn.commit()
        bookmarks = {}
    c.close()
    conn.close()
    return bookmarks  # тип данных - dict


if __name__ == '__main__':
    asyncio.run(get_dict_of_bookmarks('1071845329'))
