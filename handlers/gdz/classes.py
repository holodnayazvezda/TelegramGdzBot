from aiogram import Bot, types

from handlers.states.user_state import UserState
from utils.users.users import active_now
from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.async_process_runner import start as async_functions_process_starter
from utils.aiogram_functions_worker import try_edit_or_send_message, answer_callback_query
from utils.database.database_worker import get_information_from
from handlers.bot import BotInfo

from threading import Thread

# это функция начало гдз. Отсюда начнется первый выбор класса, первая печать InlineKeyboardButtonS
async def gdz_starter(message: types.Message, bot_instance: BotInfo):
    users_dict = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 2)
    if users_dict:
        if isinstance(message, types.Message):
            Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_instance.bot_id])).start()
            users_dict['avaliable_classes_and_links_at_it'] = list(
                map(lambda el: el[0], await get_information_from('./data/databases/gdz.sqlite3', 'classes', 'name')))
            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = []
            for z in users_dict['avaliable_classes_and_links_at_it']:
                buttons.append(types.InlineKeyboardButton(z, callback_data=z))
            markup.add(*buttons)
            message_id = await try_edit_or_send_message(user_id=message.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                        chat_id=message.chat.id,
                                                        text='Выбери свой класс!', reply_markup=markup)
            users_dict['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id),
                                                                                        bot_instance.bot_id, str(users_dict),
                                                                                        2])).start()
        elif isinstance(message, types.CallbackQuery):
            try:
                call = message
                Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_instance.bot_id])).start()
                users_dict['avaliable_classes_and_links_at_it'] = list(
                    map(lambda el: el[0], await get_information_from('./data/databases/gdz.sqlite3', 'classes', 'name')))
                markup = types.InlineKeyboardMarkup(row_width=2)
                buttons = []
                for z in users_dict['avaliable_classes_and_links_at_it']:
                    buttons.append(types.InlineKeyboardButton(z, callback_data=z))
                markup.add(*buttons)
                await answer_callback_query(call, bot_instance.bot)
                try:
                    await bot_instance.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                except Exception:
                    pass
                message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                            chat_id=call.message.chat.id,
                                                            text='Выбери свой класс!', reply_markup=markup)
                users_dict['id_of_message_with_markup'] = message_id
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id),
                                                                                            bot_instance.bot_id, str(users_dict),
                                                                                            2])).start()
            except Exception:
                pass