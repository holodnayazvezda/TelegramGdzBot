import sqlite3


async def add_payment(order_id: str, customer_id: int, customer_chat_id: int, bot_token: str, purchase_type=1):
    conn = sqlite3.connect('./data/databases/payments.sqlite3')
    c = conn.cursor()
    table_name = 'ads_payments' if purchase_type == 1 else 'premium_payments'
    c.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (order_id TEXT, customer_id INTEGER, customer_chat_id INTEGER, bot_token TEXT, processing_time INTEGER, purchase_type INTEGER)')
    if not c.execute(f'SELECT * FROM {table_name} WHERE order_id=?', (order_id,)).fetchone():
        c.execute(f'INSERT INTO {table_name} (order_id, customer_id, customer_chat_id, bot_token, processing_time, purchase_type) VALUES (?, ?, ?, ?, ?, ?)',
                  (order_id, customer_id, customer_chat_id, bot_token, 0, purchase_type))
    else:
        c.execute(f'UPDATE {table_name} SET processing_time=0 WHERE order_id=?', (order_id,))
    conn.commit()
    c.close()
    conn.close()


async def increase_processing_time(order_id: str, purchase_type=1):
    conn = sqlite3.connect('./data/databases/payments.sqlite3')
    c = conn.cursor()
    table_name = 'ads_payments' if purchase_type == 1 else 'premium_payments'
    c.execute(f'UPDATE {table_name} SET processing_time = processing_time + 1 WHERE order_id=?', (order_id,))
    conn.commit()
    c.close()
    conn.close()


async def delete_payment(order_id: str, purchase_type=1):
    conn = sqlite3.connect('./data/databases/payments.sqlite3')
    c = conn.cursor()
    table_name = 'ads_payments' if purchase_type == 1 else 'premium_payments'
    c.execute(f'DELETE FROM {table_name} WHERE order_id=?', (order_id,))
    conn.commit()
    c.close()
    conn.close()


def get_all_payments_data():
    conn = sqlite3.connect('./data/databases/payments.sqlite3')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS ads_payments (order_id TEXT, customer_id INTEGER, customer_chat_id INTEGER, bot_token TEXT, processing_time INTEGER, purchase_type INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS premium_payments (order_id TEXT, customer_id INTEGER, customer_chat_id INTEGER, bot_token TEXT, processing_time INTEGER, purchase_type INTEGER)')
    all_payments = (c.execute('SELECT * FROM ads_payments').fetchall() +
                    c.execute('SELECT * FROM premium_payments').fetchall())
    conn.commit()
    c.close()
    conn.close()
    return all_payments
