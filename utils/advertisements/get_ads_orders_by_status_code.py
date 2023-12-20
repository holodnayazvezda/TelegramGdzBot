import sqlite3
import asyncio

from utils.advertisements.ads_database_worker import get_ads_data


async def get_ads_orders_by_status_code(status_code: int = None):
    conn = sqlite3.connect('./data/databases/advertisements.sqlite3')
    c = conn.cursor()
    if status_code:
        table_names = list(map(lambda el: el[0],
                               c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()))
        ads_orders_with_transferred_status_code = {}
        for table_name in table_names:
            ads_id = table_name[4:]
            status_value_equals_with_transferred_status_code = \
                c.execute(f"SELECT * FROM {table_name} WHERE status=?", (status_code,)).fetchall()
            if status_value_equals_with_transferred_status_code:
                try:
                    ads_orders_with_transferred_status_code[ads_id] = await get_ads_data(ads_id)
                except IndexError:
                    pass
        c.close()
        conn.close()
        return ads_orders_with_transferred_status_code
    else:
        table_names = list(map(lambda el: el[0],
                               c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()))
        all_ads_orders_data = {}
        for table_name in table_names:
            ads_id = table_name[4:]
            try:
                all_ads_orders_data[ads_id] = await get_ads_data(ads_id)
            except IndexError:
                pass
        c.close()
        conn.close()
        return all_ads_orders_data


if __name__ == '__main__':
    asyncio.run(get_ads_orders_by_status_code())
