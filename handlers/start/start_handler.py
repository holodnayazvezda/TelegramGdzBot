from aiogram import types

from utils.users.users import is_new_user, active_now
from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.share.share_worker import get_shared_data
from utils.async_process_runner import start as async_functions_process_starter
from utils.aiogram_functions_worker import try_edit_or_send_message
from utils.bot.basic_prints import welcome_user
from aiogram.utils.exceptions import Unauthorized
from data.config import get_reply_markup_for_user
from handlers.bot import BotInfo
from handlers.gdz.books_and_numbers import gdz_main_function
from handlers.states.user_state import UserState

from threading import Thread


async def start(message: types.Message, bot_instance: BotInfo) -> None:
    if '/start' in message.text and len(message.text.split()) > 1:
        if message.text.split()[1].isdigit():
            referral_user_id = int(message.text.split()[1])
            if referral_user_id != message.from_user.id and await is_new_user(message.from_user.id) and not \
                    await is_new_user(referral_user_id):
                users_data = await get_dictionary(str(referral_user_id), bot_instance.bot_id, 1)
                if 'referral_users' in users_data:
                    users_data['referral_users'].add(message.from_user.id)
                else:
                    users_data['referral_users'] = set()
                    users_data['referral_users'].add(message.from_user.id)
                await create_or_dump_user(str(referral_user_id), bot_instance.bot_id, str(users_data), 1)
        else:
            solution_id = int(message.text.split()[1].replace('shared_data', ''))
            data_dict = await get_shared_data(solution_id, './data/databases/shared_data.sqlite3', 'shared_data')
            if data_dict:
                await UserState.find_solution.set()
                from aiogram.types import CallbackQuery
                message.message_id = None
                call = CallbackQuery()
                call.from_user = message.from_user
                call.message = message
                call.data = data_dict['key']
                back_to_main_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                back_to_main_menu_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
                await bot_instance.bot.send_message(message.chat.id, text='🟢', reply_markup=back_to_main_menu_markup)
                await gdz_main_function(call, bot_instance, dictionary_to_use=data_dict['all_data'])
                return
    await UserState.find_solution.set()
    conversation_id = None
    selected_model = None
    try:
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 2)
        if 'id_of_block_of_photos_send_by_bot' in dictionary_used_in_this_function and \
                dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
            for id in dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
                try:
                    await bot_instance.bot.delete_message(message.chat.id, id)
                except Exception:
                    pass
        if 'chat_gpt_conversation_id' in dictionary_used_in_this_function:
            conversation_id = dictionary_used_in_this_function['chat_gpt_conversation_id']
        if 'selected_model' in dictionary_used_in_this_function:
            selected_model = dictionary_used_in_this_function['selected_model']
        try:
            await bot_instance.bot.delete_message(message.chat.id,
                                                  dictionary_used_in_this_function['id_of_message_with_markup'])
        except Exception:
            pass
    except Exception:
        pass
    Thread(target=async_functions_process_starter,
           args=(create_or_dump_user,
                 [str(message.from_user.id), bot_instance.bot_id,
                  str({'id_of_block_of_photos_send_by_bot': [], 'id_of_messages_about_bookmarks': [],
                       'chat_gpt_conversation_id': conversation_id, 'selected_model': selected_model}), 2])).start()
    Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id,
                                                                      bot_instance.bot_id])).start()
    try:
        await try_edit_or_send_message(user_id=message.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                       chat_id=message.chat.id,
                                       text=await welcome_user(message),
                                       reply_markup=await get_reply_markup_for_user(message.from_user.id),
                                       parse_mode="markdown")
    except Unauthorized:
        print('err Unauthorized')
