from aiogram import Bot
from telebot import TeleBot


class BotInfo:
    def __init__(self, bot: Bot, bot_telebot: TeleBot, bot_id: int, token: str) -> None:
        self.bot = bot
        self.bot_telebot = bot_telebot
        self.bot_id = bot_id
        self.token = token
