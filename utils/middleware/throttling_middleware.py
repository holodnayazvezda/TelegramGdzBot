from aiogram import types, Dispatcher
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.utils.exceptions import Throttled

from telebot import TeleBot

from threading import Thread
from math import floor, ceil
import time
import redis

client = redis.Redis(host='localhost', port=6379, decode_responses=True)


def delete_messages_by_timer(delay: float, bot_token: str, message1: types.Message,
                             message2: types.Message = None) -> None:
    time.sleep(delay)
    bot_telebot = TeleBot(token=bot_token)
    if message2:
        try:
            bot_telebot.delete_message(chat_id=message2.chat.id, message_id=message2.message_id)
        except Exception:
            pass
    try:
        bot_telebot.delete_message(chat_id=message1.chat.id, message_id=message1.message_id)
    except Exception:
        pass


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, message_limit=1.15, call_limit=1, message_key_prefix='antiflood_for_messages',
                 call_key_prefix='antiflood_for_calls'):
        self.message_limit = message_limit
        self.call_limit = call_limit
        self.message_key_prefix = message_key_prefix
        self.call_key_prefix = call_key_prefix
        super(ThrottlingMiddleware, self).__init__()

    async def on_process_message(self, message: Message, data: dict) -> None:
        is_banned = client.exists(str(message.from_user.id))
        if is_banned:
            raise CancelHandler()
        dispatcher = Dispatcher.get_current()
        try:
            await dispatcher.throttle(self.message_key_prefix, rate=self.message_limit)
        except Throttled as t:
            await self.message_throttled(self, message, t)
            raise CancelHandler()

    async def on_process_callback_query(self, callback_query: CallbackQuery, data: dict) -> None:
        is_banned = client.exists(str(callback_query.from_user.id))
        if is_banned:
            raise CancelHandler()
        dispatcher = Dispatcher.get_current()
        try:
            await dispatcher.throttle(self.call_key_prefix, rate=self.call_limit)
        except Throttled as t:
            await self.callback_query_throttled(self, callback_query, t)
            raise CancelHandler()

    @staticmethod
    async def message_throttled(self, message: types.Message, throttled: Throttled) -> None:
        if throttled.exceeded_count <= 2:
            message2 = None
            try:
                if message.content_type == 'text':
                    message2 = await message.reply(f"{message.from_user.first_name}, слишком много запросов, повторите через {ceil(self.message_limit)} секунду(ы)!")
            except Exception:
                pass
            Thread(target=delete_messages_by_timer, args=(2, message.bot._token, message, message2)).start()
        else:
            if throttled.exceeded_count >= 6:
                res = client.set(name=str(message.from_user.id), value=5, ex=300)
                if res:
                    try:
                        await message.answer(f"{message.from_user.first_name}, бан на 5 минут за флуд!")
                    except Exception:
                        pass
            await message.delete()

    @staticmethod
    async def callback_query_throttled(self, callback_query: CallbackQuery, throttled: Throttled) -> None:
        if throttled.exceeded_count <= 2:
            try:
                await callback_query.answer(f"Cлишком много запросов, повторите через {floor(self.call_limit)} секунду(ы)!")
            except Exception:
                pass
        elif throttled.exceeded_count >= 6:
            res = client.set(name=str(callback_query.from_user.id), value=5, ex=300)
            if res:
                try:
                    await callback_query.answer("Бан на 5 минуты за флуд!", show_alert=True)
                except Exception:
                    pass
