import sqlite3

conn = sqlite3.connect('./data/databases/users.sqlite3')
cur = conn.cursor()

tables = list(map(lambda el: el[0], cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()))
for table_name in tables:
    if 'USERS' not in table_name:
        data = cur.execute(f"SELECT data FROM {table_name}").fetchone()[0]
        cur.execute(f'DROP TABLE {table_name}')
        cur.execute(f'CREATE TABLE {table_name} (data TEXT, data_5513797718 TEXT)')
        cur.execute(f'INSERT INTO {table_name} (data, data_5513797718) VALUES (?, ?)', (str({'bookmarks': {}, 'bots': {}}), data))
        print(table_name)
conn.commit()
cur.close()
conn.close()
