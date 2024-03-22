import asyncio
from aiogram.utils.exceptions import MessageNotModified, CantParseEntities
from aiogram import Bot, types
from telebot import TeleBot
from threading import Thread

from utils.advertisements.ads_user_worker import *
from utils.async_process_runner import start


def cut_the_message_text(message_text):
    if len(message_text) >= 4096:
        return message_text[:4092] + '...'
    return message_text


async def try_edit_or_send_message(user_id: int, bot: Bot, bot_id: int, chat_id: int, text: str, message_id: int=None, reply_markup=None,
                                   parse_mode: str = None, do_not_add_ads: bool = False) -> int:
    ads_data_for_user = await get_ads_for_user(user_id, bot_id, do_not_add_ads)
    if ads_data_for_user:
        if parse_mode:
            text += f'\n\n*📢 Реклама:* _{ads_data_for_user[1][-3]}_'
        else:
            text += f'\n\n📢 Реклама: {ads_data_for_user[1][-3]}'
    try:
        x = await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=cut_the_message_text(text),
                                        reply_markup=reply_markup, parse_mode=parse_mode)
        if ads_data_for_user:
            await view_ads_by_user(user_id, bot_id, ads_data_for_user[0])
        return x.message_id
    except MessageNotModified:
        pass
    except CantParseEntities:
        return await try_edit_or_send_message(user_id, bot, bot_id, chat_id, text, message_id, reply_markup, None, True)
    except Exception:
        try:
            if message_id:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except Exception:
                    pass
            x = await bot.send_message(chat_id=chat_id, text=cut_the_message_text(text), reply_markup=reply_markup, parse_mode=parse_mode)
            if ads_data_for_user:
                await view_ads_by_user(user_id, bot_id, ads_data_for_user[0])
            return x.message_id
        except CantParseEntities:
            return await try_edit_or_send_message(user_id, bot, bot_id, chat_id, text, message_id, reply_markup, None,
                                                  True)


async def send_message(user_id: int, bot: Bot, bot_id: int, chat_id: int, text: str, message_id: int=None, reply_markup=None, parse_mode: str=None,
                       do_not_add_ads: bool=False):
    ads_data_for_user = await get_ads_for_user(user_id, bot_id, do_not_add_ads)
    if ads_data_for_user:
        if parse_mode:
            text += f'\n\n*📢 Реклама:* _{ads_data_for_user[1][-3]}_'
        else:
            text += f'\n\n📢 Реклама: {ads_data_for_user[1][-3]}'
    if message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
    try:
        x = await bot.send_message(chat_id=chat_id, text=cut_the_message_text(text), reply_markup=reply_markup,
                                   parse_mode=parse_mode)
        if ads_data_for_user:
            await view_ads_by_user(user_id, bot_id, ads_data_for_user[0])
        return x.message_id
    except CantParseEntities:
        return await send_message(user_id, bot, bot_id, chat_id, text, message_id, reply_markup, None, True)


async def send_photo(user_id: int, bot: Bot, bot_id: int, chat_id: int, photo, caption: str=None, message_id: int=None, reply_markup=None,
                     parse_mode: str=None, do_not_add_ads: bool=False):
    ads_data_for_user = await get_ads_for_user(user_id, bot_id, do_not_add_ads)
    if ads_data_for_user and caption:
        if parse_mode:
            caption += f'\n\n*📢 Реклама:* _{ads_data_for_user[1][-3]}_'
        else:
            caption += f'\n\n📢 Реклама: {ads_data_for_user[1][-3]}'
    if message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
    try:
        x = await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup,
                                 parse_mode=parse_mode)
        if ads_data_for_user:
            await view_ads_by_user(user_id, bot_id, ads_data_for_user[0])
        return x.message_id
    except CantParseEntities:
        return await send_photo(user_id, bot, bot_id, chat_id, caption, photo, message_id, reply_markup, None, True)


def send_message_by_telebot(user_id: int, bot_telebot: TeleBot, bot_id: int, chat_id: int, text: str, message_id: int=None, reply_markup=None,
                            parse_mode: str=None, do_not_add_ads: bool=False):
    future = asyncio.Future()

    async def wrapper():
        future.set_result(await get_ads_for_user(user_id, bot_id, do_not_add_ads))

    t = Thread(target=start, args=(wrapper, []))
    t.start()
    t.join()
    ads_data_for_user = future.result()
    if ads_data_for_user:
        if parse_mode:
            text += f'\n\n*📢 Реклама:* _{ads_data_for_user[1][-3]}_'
        else:
            text += f'\n\n📢 Реклама: {ads_data_for_user[1][-3]}'
    if message_id:
        try:
            bot_telebot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
    try:
        x = bot_telebot.send_message(chat_id=chat_id, text=cut_the_message_text(text), reply_markup=reply_markup,
                                     parse_mode=parse_mode)
        if ads_data_for_user:
            Thread(target=start, args=(view_ads_by_user, [user_id, bot_id, ads_data_for_user[0]])).start()
        return x.message_id
    except Exception as e:
        if "find end of the entity" in str(e).lower():
            return send_message_by_telebot(user_id, bot_telebot, bot_id, chat_id, text, message_id, reply_markup, None, True)


async def answer_callback_query(call: types.CallbackQuery, bot: Bot, text: str=None, show_alert: bool=False):
    try:
        await bot.answer_callback_query(callback_query_id=call.id, text=text, show_alert=show_alert)
    except Exception:
        pass
