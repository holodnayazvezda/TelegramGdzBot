import sqlite3


def get_tablename_by_provider(provider: int):
    if provider == 1:
        return 'OPENAI'
    elif provider == 2:
        return 'SHUTTLEAI'


def get_working_api_keys(provider: int):
    conn = sqlite3.connect("./data/databases/apikeys.sqlite3")
    c = conn.cursor()
    data = list(map(lambda el: el[0],
                    c.execute(f"SELECT api_key FROM {get_tablename_by_provider(provider)} WHERE use=1").fetchall()))
    conn.close()
    return data


async def start_or_stop_api_key(provider: int, api_key: str, action: int):
    conn = sqlite3.connect("./data/databases/apikeys.sqlite3")
    c = conn.cursor()
    c.execute(f'UPDATE {get_tablename_by_provider(provider)} SET use=? WHERE api_key=?', (action, api_key))
    conn.commit()
    conn.close()


async def add_api_key(provider: int, email: str, password: str, api_key: str, expires: str):
    conn = sqlite3.connect("./data/databases/apikeys.sqlite3")
    c = conn.cursor()
    c.execute(
        f'INSERT INTO {get_tablename_by_provider(provider)} (email, password, api_key, use, expires) VALUES (?, ?, ?, ?, ?)',
        (email, password, api_key, 1, expires))
    conn.commit()
    conn.close()


OPENAI_API_KEYS = get_working_api_keys(1)
SHUTTLEAI_API_KEYS = get_working_api_keys(2)
counter_of_requests = 0


async def update_api_keys():
    global OPENAI_API_KEYS, SHUTTLEAI_API_KEYS
    OPENAI_API_KEYS = get_working_api_keys(1)
    SHUTTLEAI_API_KEYS = get_working_api_keys(2)
