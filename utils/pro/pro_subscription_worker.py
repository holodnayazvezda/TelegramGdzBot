import sqlite3
import datetime as dt
from telebot import types, TeleBot

from data.config import ADMINS, AMOUNT_OF_REFERRALS_FOR_PRO
from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.chatgpt.chat_gpt_users_worker import get_amount_of_referrals


async def is_pro(user_id: int) -> bool:
    if str(user_id) in ADMINS:
        return True
    try:
        if (await get_amount_of_referrals(user_id, 5513797718)) >= AMOUNT_OF_REFERRALS_FOR_PRO:
            return True
    except Exception:
        pass
    conn = sqlite3.connect('./data/databases/pro_users.sqlite3')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS pro_users_data (id INTEGER, creation_date TEXT, months INTEGER, expired_date TEXT, chat_id INTEGER, bot_token TEXT)')
    has_pro = c.execute('SELECT * FROM pro_users_data WHERE id=?', (user_id,)).fetchall()
    c.close()
    conn.close()
    if has_pro:
        return True
    return False


async def set_pro_for_user(user_id: int, months: int, chat_id: int, bot_token: str) -> None:
    if not await is_pro(user_id):
        users_data = await get_dictionary(str(user_id), None, 1)
        if 'have_had_pro' not in users_data:
            users_data['have_had_pro'] = True
            await create_or_dump_user(str(user_id), None, str(users_data), 1)
        conn = sqlite3.connect('./data/databases/pro_users.sqlite3')
        c = conn.cursor()
        date_now = dt.datetime.now()
        expired_date = (date_now + dt.timedelta(days=months*30)).strftime("%y-%m-%d:%H")
        c.execute('CREATE TABLE IF NOT EXISTS pro_users_data (id INTEGER, creation_date TEXT, months INTEGER, expired_date TEXT, chat_id INTEGER, bot_token TEXT)')
        c.execute('INSERT INTO pro_users_data (id, creation_date, months, expired_date, chat_id, bot_token) VALUES (?, ?, ?, ?, ?, ?)',
                  (user_id, str(date_now), months, str(expired_date), chat_id, bot_token))
        conn.commit()
        c.close()
        conn.close()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text='👌 Хорошо', callback_data='delete_this_message'))
        bot = TeleBot(token=bot_token, parse_mode=None)
        months_text = f'{months} месяц'
        if months == 3:
            months_text += 'а'
        elif months == 6:
            months_text += 'ев'
        id_of_pay_premium_message = None
        if 'id_of_pay_premium_message' in users_data:
            id_of_pay_premium_message = users_data['id_of_pay_premium_message']
            del users_data['id_of_pay_premium_message']
            await create_or_dump_user(str(user_id), None, str(users_data), 1)
        pro_subscription_was_bought_message_text = f'💎 Поздравляем с приобретением подписки ReshenijaBot PRO на *{months_text}*. Теперь *реклама отключена*, и вам *доступны эксклюзивные функции*!'
        try:
            if id_of_pay_premium_message:
                try:
                    new_markup = types.InlineKeyboardMarkup()
                    new_markup.add(types.InlineKeyboardButton(text='👌 Хорошо',
                                                          callback_data='delete_this_message_and_go_to_my_account'))
                    bot.edit_message_text(chat_id=chat_id, message_id=id_of_pay_premium_message,
                                          text=pro_subscription_was_bought_message_text, reply_markup=new_markup,
                                          parse_mode='markdown')
                except Exception:
                    bot.send_message(chat_id=chat_id, text=pro_subscription_was_bought_message_text,
                                     reply_markup=markup, parse_mode='markdown')
            else:
                bot.send_message(chat_id=chat_id, text=pro_subscription_was_bought_message_text, reply_markup=markup,
                                 parse_mode='markdown')
        except Exception:
            pass


async def unsubscribe_users_from_pro(date_now: str) -> None:
    conn = sqlite3.connect('./data/databases/pro_users.sqlite3')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS pro_users_data (id INTEGER, creation_date TEXT, months INTEGER, expired_date TEXT, chat_id INTEGER, bot_token TEXT)')
    users_datas = c.execute('SELECT chat_id, bot_token FROM pro_users_data WHERE expired_date<=?', (date_now,)).fetchall()
    c.execute('DELETE FROM pro_users_data WHERE expired_date<=?', (date_now,))
    conn.commit()
    c.close()
    conn.close()
    for user_data in users_datas:
        markup = types.InlineKeyboardMarkup()
        markup.add(*[types.InlineKeyboardButton(text='👌 Хорошо', callback_data='delete_this_message'),
                     types.InlineKeyboardButton(text='💎 Продлить подписку', callback_data='extend_subscription')])
        bot = TeleBot(token=user_data[1], parse_mode=None)
        pro_subscription_has_expired = '❗ Ваша PRO подписка истекла. Доступ к эксклюзивным функциям приостановлен. Вы можете продлить ее в личном кабинете или, нажав на кнопку ниже.'
        try:
            bot.send_message(chat_id=user_data[0], text=pro_subscription_has_expired, reply_markup=markup,
                             parse_mode='markdown')
        except Exception:
            pass


async def get_the_rest_of_the_subscription_days(user_id: int) -> tuple:
    conn = sqlite3.connect('./data/databases/pro_users.sqlite3')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS pro_users_data (id INTEGER, creation_date TEXT, months INTEGER, expired_date TEXT, chat_id INTEGER, bot_token TEXT)')
    rest_of_days = c.execute('SELECT expired_date FROM pro_users_data WHERE id=?', (user_id,)).fetchone()
    c.close()
    conn.close()
    if rest_of_days:
        expired_date = dt.datetime.strptime(rest_of_days[0], "%y-%m-%d:%H")
        current_date = dt.datetime.now()
        difference = expired_date - current_date
        years_remaining, months_remaining, days_remaining = (difference.days // 365, (difference.days % 365) // 30,
                                                             (difference.days % 365) % 30)
        return years_remaining, months_remaining, days_remaining
    return ()
