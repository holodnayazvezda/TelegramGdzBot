from aiogram import types

TOKEN = '5513797718:AAFuDfJrAOncsA4wVnW6np3uQ37h4tyKB0E'
TEST_TOKEN = '5545579241:AAFILdiP0FNyb8SSMmB1l8cTZ9n7E24VD0E'
TEST_YANDEX_TOKEN = '6196558028:AAF9018kclwlwHYwGU6_yGowYwyu8KjO8s0'
PAYMENTS_YOOMONEY_TOKEN = '4100118315446381.A2E7157A96052222CADBFED724293D1AF4AB74B9436A192E6E0EC8CD845B8A64E6BDC15F8EB83982D0C19FA4212B12BAEA3095A80E210584ED41082C90BF8733276B07D38F6936F6EA7323FE221081CBD47992AFCE1DEEC949A664E839435F5F3D4DACCE049ED7B1E36DFE764E1BD4A24124BB54714198E22E0D9B07EC9F3309'
OCR_SPACE_API_KEYS = ['K85720388688957', 'K89292650388957', 'K89083415488957', 'K84384523188957', 'K89142091988957',
                      'K87164054488957', 'K84054502088957', 'K82657306788957', 'K83028254688957', 'K81585714888957',
                      'K84731190188957', 'K84676433588957', 'K89859164888957', 'K87616973288957', 'K83094111388957']
amount_of_requests_to_ocr_api = 0
LENGTH_OF_GPT3_HISTORY_FOR_USERS = 5
LENGTH_OF_GPT3_HISTORY_FOR_PRO_USERS = 12
LENGTH_OF_GPT4_HISTORY_FOR_USERS = 2
LENGTH_OF_GPT4_HISTORY_FOR_PRO_USERS = 6
PROMPT_FROM_USER_MAX_LENGTH = 2048
HEADERS = {
    'Accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0'
}
ADMINS = ['1071845329', '1925785299']
MAIN_BUTTONS = ['⁉️ Найти решение', '🤖 ИИ Chat GPT', '📌 Закладки', '👤 Мой аккаунт', '📊 Статистика',
                'ℹ️ Информация о боте', '🏟 Реклама', '👮 Для правообладателей контента', '👨‍💻 Для пользователей']
COOKIES_FOR_GPT_4_BING_USERS = {"set-cookie": "MUIDB=3C770E47015963000FB21D85000E62EB; expires=Sun, 01-Dec-2024 23:04:06 GMT; path=/; HttpOnly", "useragentreductionoptout": "A7kgTC5xdZ2WIVGZEfb1hUoNuvjzOZX3VIV/BA6C18kQOOF50Q0D3oWoAm49k3BQImkujKILc7JmPysWk3CSjwUAAACMeyJvcmlnaW4iOiJodHRwczovL3d3dy5iaW5nLmNvbTo0NDMiLCJmZWF0dXJlIjoiU2VuZEZ1bGxVc2VyQWdlbnRBZnRlclJlZHVjdGlvbiIsImV4cGlyeSI6MTY4NDg4NjM5OSwiaXNTdWJkb21haW4iOnRydWUsImlzVGhpcmRQYXJ0eSI6dHJ1ZX0="}
COOKIES_FOR_GPT_4_BING_PRO_USERS = {"set-cookie": "MUIDB=3C770E47015963000FB21D85000E62EB; expires=Sat, 21-Dec-2024 21:57:35 GMT; path=/; HttpOnly", "useragentreductionoptout": "A7kgTC5xdZ2WIVGZEfb1hUoNuvjzOZX3VIV/BA6C18kQOOF50Q0D3oWoAm49k3BQImkujKILc7JmPysWk3CSjwUAAACMeyJvcmlnaW4iOiJodHRwczovL3d3dy5iaW5nLmNvbTo0NDMiLCJmZWF0dXJlIjoiU2VuZEZ1bGxVc2VyQWdlbnRBZnRlclJlZHVjdGlvbiIsImV4cGlyeSI6MTY4NDg4NjM5OSwiaXNTdWJkb21haW4iOnRydWUsImlzVGhpcmRQYXJ0eSI6dHJ1ZX0="}
AMOUNT_OF_REFERRALS_FOR_PRO = 5


async def get_buttons_list_for_user(user_id):
    if str(user_id) in ADMINS:
        return ['⁉️ Найти решение', '🤖 ИИ Chat GPT', '📌 Закладки', '👤 Мой аккаунт', '📈 Статистика',
                'ℹ️ Информация о боте', '🏟 Реклама', '💻 Для разработчиков', '👮 Для правообладателей контента',
                '👨‍💻 Для пользователей']
    return ['⁉️ Найти решение', '🤖 ИИ Chat GPT', '📌 Закладки', '👤 Мой аккаунт', '📈 Статистика',
            'ℹ️ Информация о боте', '🏟 Реклама', '👮 Для правообладателей контента', '👨‍💻 Для пользователей']


async def get_reply_markup_for_user(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = []
    for btn_text in await get_buttons_list_for_user(user_id):
        buttons.append(types.KeyboardButton(btn_text))
    markup.add(*buttons)
    return markup


MAIN_COMMANDS = ['/chat_gpt', '/statistics', '/bookmarks', '/my_account', '/gift', '/unsubscribe']
BOT_USERNAME = '@ReshenijaBot'
BOT_VERSION = '4.5'
BOT_RELEASE_NAME = 'Maysky'
BOT_TELEGRAM_CHANNEL_USERNAME = '@ReshenijaBotChannel'
BOT_TELEGRAM_GROUP_USERNAME = '@ReshenijaBotChat'
SUPPORT_BOT_USERNAME = '@ReshenijaSupportBot'


PRICE_FOR_WATCH = 0.05
PRICES_FOR_ADS = {500: 25, 1000: 50, 10000: 475, 20000: 950, 100000: 4500}
PRICES_FOR_PREMIUM = {'1 месяц': 100, '3 месяца': 250, '6 месяцев': 500}


async def get_available_amount_of_bookmarks(id, have_had_premium, has_working_bots, amount_of_referrals):
    if str(id) in ADMINS:
        return 99
    else:
        if have_had_premium:
            min_amount_of_bookmarks = 60
        else:
            min_amount_of_bookmarks = 30
        if has_working_bots:
            return min([99, min_amount_of_bookmarks + 15 + amount_of_referrals])
        return min([99, min_amount_of_bookmarks + amount_of_referrals])


async def get_max_tokens_in_response_for_user(has_pro: bool):
    max_tokens = PROMPT_FROM_USER_MAX_LENGTH
    if has_pro:
        max_tokens *= 2
    return int(max_tokens)


async def get_available_amount_of_requests_to_chat_gpt(has_pro: bool, model: str, has_working_bots: bool,
                                                       amount_of_referrals: int):
    if model in ['gpt-4', 'gpt-4-bing']:
        if has_pro:
            return 50
        else:
            amount_of_requests = 3
            amount_of_requests += amount_of_referrals
            if has_working_bots:
                amount_of_requests *= 2
            return amount_of_requests
    else:
        if has_pro:
            return 200
        else:
            return 30
