import sqlite3
from telebot import types, TeleBot
from threading import Thread

from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.users.users import get_bot_token_and_admin_chat_id
from data.config import ADMINS
from utils.async_process_runner import start


async def send_ads_on_moderation(ads_id: int, customer_id: int, watches_ordered: int, price, text: str) -> None:
    markup = types.InlineKeyboardMarkup()
    markup.add(*[types.InlineKeyboardButton(text='✅', callback_data=f'pass_moderation_{ads_id}'),
                 types.InlineKeyboardButton(text='❌', callback_data=f'reject_moderation_{ads_id}')])
    send_ads_on_moderation_message_text = f'🆕 Новый рекламный заказ на модерацию.\n\n👤 От *{customer_id}*\n🆔 id рекламного объявления: *{ads_id}*\n\n📝 Текст: *{text}*\n\n👀 Заказано просмотров: *{watches_ordered}*\n💸 На сумму: *{price}₽*'
    bots_tokens_and_chats_ids = await get_bot_token_and_admin_chat_id()
    for bot_token_and_chat_id in bots_tokens_and_chats_ids:
        bot = TeleBot(token=bot_token_and_chat_id[0], parse_mode=None)
        try:
            bot.send_message(chat_id=bot_token_and_chat_id[1], text=send_ads_on_moderation_message_text,
                             reply_markup=markup, parse_mode='markdown')
        except Exception:
            pass


async def create_ads(customer_id: int, customer_chat_id: int, bot_token: str,
                     watches_ordered: int, price: int, text: str) -> int:
    if str(customer_id) in ADMINS:
        status = 4
    else:
        status = 1
    conn = sqlite3.connect('./data/databases/advertisements.sqlite3')
    c = conn.cursor()
    id_of_ads = await get_next_id_from_database()
    c.execute(f'CREATE TABLE IF NOT EXISTS ads_{id_of_ads} (customer_id INTEGER, customer_chat_id INTEGER, bot_token TEXT, watches_ordered INTEGER, price REAL, text TEXT, amount_of_watches INTEGER, status INTEFGER)')
    c.execute(f'INSERT INTO ads_{id_of_ads} (customer_id, customer_chat_id, bot_token, watches_ordered, price, text, amount_of_watches, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
              (customer_id, customer_chat_id, bot_token, watches_ordered, price, text, 0, status))
    conn.commit()
    c.close()
    conn.close()
    if status == 1:
        await send_ads_on_moderation(id_of_ads, customer_id, watches_ordered, price, text)
    return id_of_ads


async def get_ads_data(ads_id: int) -> dict:
    conn = sqlite3.connect('./data/databases/advertisements.sqlite3')
    c = conn.cursor()
    data = c.execute(f'SELECT * FROM ads_{ads_id}').fetchone()
    c.close()
    conn.close()
    return {'customer_id': data[0], 'watches_ordered': data[3], 'price': data[4], 'text': data[5],
            'amount_of_watches': data[6], 'status': data[7]}


async def add_watcher(ads_id: int) -> None:
    conn = sqlite3.connect('./data/databases/advertisements.sqlite3')
    c = conn.cursor()
    c.execute(f'UPDATE ads_{ads_id} SET amount_of_watches=?', (c.execute(f'SELECT amount_of_watches FROM ads_{ads_id}').fetchone()[0] + 1,))
    conn.commit()
    c.close()
    conn.close()
    ads_data = await get_ads_data(ads_id)
    if int(ads_data['watches_ordered']) == int(ads_data['amount_of_watches']):
        await change_ads_status(ads_id, 5)


async def get_next_id_from_database() -> int:
    conn = sqlite3.connect('./data/databases/advertisements.sqlite3')
    c = conn.cursor()
    try:
        next_id = sorted(list(map(lambda el: int(el[0].split('_')[-1]), c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall())), reverse=True)[0] + 1
    except Exception:
        next_id = 1
    c.close()
    conn.close()
    return next_id


async def get_ads_owner_chat_data(ads_id: int) -> dict:
    conn = sqlite3.connect('./data/databases/advertisements.sqlite3')
    c = conn.cursor()
    data = c.execute(f'SELECT customer_chat_id, bot_token FROM ads_{ads_id}').fetchone()
    c.close()
    conn.close()
    return {'chat_id': data[0], 'bot_token': data[1]}


async def change_ads_status(ads_id: int, new_status: int, sending_data=None, do_not_send_message: bool = False):
    conn = sqlite3.connect('./data/databases/advertisements.sqlite3')
    c = conn.cursor()
    current_status = c.execute(f'SELECT status FROM ads_{ads_id}').fetchone()[0]
    if current_status >= new_status:
        raise Exception('Ошибка! Статус не может быть изменен так как ранне этот рекламное объявление уже имело следующий статус')
    else:
        c.execute(f'UPDATE ads_{ads_id} SET status=?', (new_status,))
    conn.commit()
    c.close()
    conn.close()
    if new_status == 2:
        markup = types.InlineKeyboardMarkup()
        markup.add(*[types.InlineKeyboardButton(text='📁 Открыть объявление', callback_data=f'ads_{ads_id}'),
                     types.InlineKeyboardButton(text='➕ Создать новое объявление', callback_data='create_ads')])
        data_to_send = await get_ads_owner_chat_data(ads_id)
        bot = TeleBot(token=data_to_send['bot_token'], parse_mode=None)
        message_text = f'❌ К сожалению объявление *№{ads_id}* не прошло модерацию.\n\nВозможные причины:\n-Некорректное описание или содержит ошибки.\n-Указание более одного @username или более одной ссылки.\n- Несуществующий @username или несуществующая ссылка.\n- Нарушает наши условия (ставки, сомнительные проекты).\n- Приватный канал.'
        try:
            bot.send_message(chat_id=data_to_send['chat_id'], text=message_text, reply_markup=markup,
                             parse_mode='markdown')
        except Exception:
            pass
    elif new_status == 3:
        markup = types.InlineKeyboardMarkup()
        markup.add(*[types.InlineKeyboardButton(text='💳 Оплатить', callback_data=f'pay_{ads_id}'),
                     types.InlineKeyboardButton(text='📁 Открыть объявление', callback_data=f'ads_{ads_id}')])
        data_to_send = await get_ads_owner_chat_data(ads_id)
        bot = TeleBot(token=data_to_send['bot_token'], parse_mode=None)
        message_text = f'✅ Объявление *№{ads_id}* прошло модерацию.\n\nТеперь его нужно оплатить. Вы можете это сделать сейчас, а можете пойже в меню *"🏟 Реклама" ➡️ "📥 Управление объявлениями" ➡️ "№{ads_id}"*.'
        try:
            bot.send_message(chat_id=data_to_send['chat_id'], text=message_text, reply_markup=markup,
                             parse_mode='markdown')
        except Exception:
            pass
    elif new_status == 4 or new_status == 5 and not do_not_send_message:
        customer_data = await get_ads_data(ads_id)
        users_data = await get_dictionary(str(customer_data['customer_id']), 0, 1)
        markup = types.InlineKeyboardMarkup()
        markup.add(*[types.InlineKeyboardButton(text='👌 Хорошо', callback_data='delete_this_message'),
                     types.InlineKeyboardButton(text='📁 Открыть объявление', callback_data=f'ads_{ads_id}')])
        bot = TeleBot(token=sending_data['bot_token'], parse_mode=None)
        if new_status == 4:
            message_text = f'💸 Объявление *№{ads_id}* оплачено. Его показ запущен.'
        else:
            message_text = f'✅ Показ объявления *№{ads_id}* завершён.'
        id_of_ads_paid_message = None
        if 'id_of_ads_paid_message' in users_data:
            id_of_ads_paid_message = users_data['id_of_ads_paid_message']
            del users_data['id_of_ads_paid_message']
            Thread(target=start, args=(create_or_dump_user, [str(customer_data['customer_id']), None, str(users_data),
                                                             1])).start()
        try:
            if id_of_ads_paid_message:
                try:
                    new_markup = types.InlineKeyboardMarkup()
                    new_markup.add(*[
                        types.InlineKeyboardButton(text='👌 Хорошо',
                                                   callback_data='delete_this_message_and_open_advertisement_cabinet'),
                        types.InlineKeyboardButton(text='📁 Открыть объявление', callback_data=f'ads_{ads_id}')])
                    bot.edit_message_text(chat_id=sending_data['chat_id'], message_id=id_of_ads_paid_message,
                                          text=message_text, reply_markup=new_markup, parse_mode='markdown')
                except Exception:
                    bot.send_message(chat_id=sending_data['chat_id'], text=message_text, reply_markup=markup,
                                     parse_mode='markdown')
            else:
                bot.send_message(chat_id=sending_data['chat_id'], text=message_text, reply_markup=markup,
                                 parse_mode='markdown')
        except Exception:
            pass


async def get_paid_ads() -> dict:
    conn = sqlite3.connect('./data/databases/advertisements.sqlite3')
    c = conn.cursor()
    ads_tables_names = list(map(lambda el: el[0],
                                c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()))
    paid_ads_data = {}
    for ads_table_name in ads_tables_names:
        data = c.execute(f'SELECT * FROM {ads_table_name} WHERE status = 4').fetchone()
        if data:
            paid_ads_data[int(ads_table_name.split('_')[-1])] = data
    c.close()
    conn.close()
    return paid_ads_data
