from aiogram import types

from utils.bot.bots_worker import get_amount_of_users
from data.config import BOT_USERNAME, BOT_VERSION, BOT_TELEGRAM_CHANNEL_USERNAME, BOT_TELEGRAM_GROUP_USERNAME, \
    BOT_RELEASE_NAME, SUPPORT_BOT_USERNAME
from utils.users.users import active_now
from utils.async_process_runner import start

import sqlite3
from threading import Thread


async def welcome_user(message: types.Message) -> str:
    return f'''
🖐 Привет, {message.from_user.first_name}, выбери желаемое действие!

🗣 Наш канал: *{BOT_TELEGRAM_CHANNEL_USERNAME}*
👥 Наш чат: *{BOT_TELEGRAM_GROUP_USERNAME}*'''


async def get_amount_of_users_in_all_bots() -> int:
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    try:
        amount_of_users = c.execute('SELECT COUNT(id) FROM USERS').fetchone()[0]
    except IndexError:
        amount_of_users = 1
    c.close()
    conn.close()
    return amount_of_users


async def check_amount_of_users(message: types.Message, bot_id: int) -> str:
    Thread(target=start, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
    conn = sqlite3.connect('./data/databases/users.sqlite3')
    c = conn.cursor()
    try:
        amount_of_daily_users = c.execute(f'SELECT COUNT(id) FROM DAILY_USERS').fetchone()[0]
    except IndexError:
        amount_of_daily_users = 1
    c.close()
    conn.close()
    users_in_this_bot, daily_users_in_this_bot = await get_amount_of_users(bot_id)
    return f"ℹ️ Общее количество пользователей бота: {await get_amount_of_users_in_all_bots()}, активных за сегодня: {amount_of_daily_users}.\n\n🤖 Количесво пользователей в этом боте: {users_in_this_bot}, активных за сегодня: {daily_users_in_this_bot}."


async def for_content_owners(message: types.Message, bot_id: int) -> str:
    Thread(target=start, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
    return 'Изображения обложек учебников, а также выдержки из соответствующих учебных пособий предоставлены ' \
           'исключительно для удобства пользователей. Использование выдержек из учебных пособий в "разумных ' \
           'пределах", и использование изображений обложек учебников допускается в силу положения статьи 1274 ' \
           'Гражданского кодекса Российской Федерации. Источником изображений, присылаемых ботом, в виде фото-ответа ' \
           'в личные сообщения и/или сообщений в групповой чат пользователям, является сайт (источник) ' \
           'https://megaresheba.ru. Они (изображения решений номеров) носят исключительно цитируемый характер и ' \
           'предоставляются исключительно в учебных(образовательных) и культурных целях (в соответствии с пунктами 1, ' \
           '4 части 1 статьи 1274 Гражданского кодекса Российской Федерации). Проект @ReshenijaBot является ' \
           'некоммерческим, он не генерирует никакой прибыли. Единственная цель, с которой создавался этот бот (' \
           'проект @ReshenijaBot) — это ускорить и упростить поиск ответа на трудное и нелюбимое задание. Контент ' \
           'Chat GPT, предоставляемый ботом, получен благодаря нейросети chat gpt и ее api (' \
           'https://chat.openai.com).'


async def for_users(message: types.Message, bot_id: int) -> str:
    Thread(target=start, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
    return f'''❤️ Спасибо, что пользуетесь @ReshenijaBot!

📢 Наш канал: *{BOT_TELEGRAM_CHANNEL_USERNAME}*
👥 Наш чат: *{BOT_TELEGRAM_GROUP_USERNAME}*
🛟 Поддержка: *{SUPPORT_BOT_USERNAME}*

ℹ️ *Общая информация*:
Хотим уведомить Вас о том, что создатель бота (@ReshenijaBot), далее - бот, не несет ответственности за любой ущерб, возникший в результате вашего использования и/или невозможности использования бота и информации, предоставляемой им, а также достоверности и/или недостоверности информации, предоставляемой ботом!

🤖 *Chat GPT*:
Сегодня искусственный интеллект стремительно развивается. Благодаря компании Open AI каждый из нас может совершенно бесплатно получить доступ к лучшему искусственному интеллекту в истории. Благодаря этому спектр задач, которые может решать бот увеличился. Создатель бота надеется, что вы, уважаемые пользователи, по-достоинству оцените эти новые возможности. Я делаю все возможное для того, чтобы бот поддерживал Chat GPT. Но мне бы хотелось заранее предупредить вас о том, что если доступ к этому искусственному интеллекту станет полностью недоступен, то из бота он пропадет. 

*Желаю приятно пользования и быстрого поиска ответов!*
'''


async def bot_information(message: types.Message, bot_id: int) -> str:
    Thread(target=start, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
    return f''' 🤖: Вы используете *{BOT_USERNAME}*

#⃣ : Текущая версия бота - *{BOT_VERSION}*

🗓: Релиз - *{BOT_RELEASE_NAME}*

Рекомендуем подписаться на наш телеграмм канал 
📢 *{BOT_TELEGRAM_CHANNEL_USERNAME}* и чат
👥 *{BOT_TELEGRAM_GROUP_USERNAME}*!
В них вы найдете полезную информацию о боте, его обновлениях, новых функциях и других проектах.

❤️ Сделано в *России 🇷🇺*
🐍 Написано на *Python*
'''
