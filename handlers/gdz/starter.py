from aiogram import types

from utils.async_process_runner import start as async_functions_process_starter
from utils.users.users import active_now
from handlers.bot import BotInfo
from handlers.gdz.classes import gdz_starter
from handlers.states.user_state import UserState

from threading import Thread


# это функция, отвечающая за обработку нажатия на 'найти решение'
async def find_solution(message, bot_instance: BotInfo):
    Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_instance.bot_id])).start()
    back_to_main_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_to_main_menu_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
    await bot_instance.bot.send_message(message.chat.id, text='🟢', reply_markup=back_to_main_menu_markup)
    await gdz_starter(message, bot_instance)
    await UserState.find_solution.set()