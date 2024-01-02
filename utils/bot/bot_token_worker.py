import asyncio

from telebot import TeleBot
from telebot.apihelper import ApiTelegramException


async def check_bot_token(bot_token: str) -> dict:
    try:
        bot = TeleBot(token=bot_token, parse_mode=None)
        bot_info = bot.get_me()
        if bot_info is not None:
            return {'ok': True, 'data': {'name': bot_info.full_name, 'username': bot_info.username}}
    except ApiTelegramException:
        return {'ok': False, 'data': {'name': None, 'username': None}}


async def get_bot_info(bot_token: str) -> dict:
    try:
        bot = TeleBot(token=bot_token, parse_mode=None)
        bot_info = bot.get_me()
        if bot_info is not None:
            return {'name': bot_info.full_name, 'username': bot_info.username}
    except ApiTelegramException:
        return {'name': None, 'username': None}


if __name__ == '__main__':
    asyncio.run(check_bot_token('5782241319:AAHTUz-olqbQd-xeA2EM9vDQELrpgt6a9AA'))