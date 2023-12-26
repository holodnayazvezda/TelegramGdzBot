from aiogram import types, Bot
from aiogram.dispatcher import FSMContext

from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.async_process_runner import start as async_functions_process_starter
from utils.users.users import active_now
from utils.pro.pro_subscription_worker import is_pro
from utils.chatgpt.requests_counter import get_amount_of_requests_for_user
from utils.aiogram_functions_worker import try_edit_or_send_message
from utils.chatgpt.chat_gpt_users_worker import get_has_working_bots, get_amount_of_referrals
from handlers.gpt.gpt_message_handlers import chat_gpt_starter
from handlers.states.user_state import UserState
from data.config import get_available_amount_of_requests_to_chat_gpt
from handlers.bot import BotInfo

from threading import Thread



async def chat_gpt_inline_buttons_handler(call: types.CallbackQuery, state: FSMContext, bot_instance: BotInfo):
    if call.data == 'back_to_model_selection':
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_instance.bot_id, 2)
        dictionary_used_in_this_function['text_get_for_chat_gpt'] = False
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
        await chat_gpt_starter(call, bot_instance)


async def get_chat_gpt_version(call: types.CallbackQuery, state: FSMContext, bot_instance: BotInfo):
    Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_instance.bot_id])).start()
    dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_instance.bot_id, 2)
    if 'gpt-' in call.data:
        users_data = await get_dictionary(str(call.from_user.id), bot_instance.bot_id, 1)
        has_working_bots = await get_has_working_bots(call.from_user.id, bot_instance.bot_id, users_data)
        amount_of_referrals = await get_amount_of_referrals(call.from_user.id, bot_instance.bot_id, users_data)
        selected_model = call.data
        dictionary_used_in_this_function['selected_model'] = selected_model
        has_pro = await is_pro(call.from_user.id)
        if selected_model == 'gpt-4-bing':
            table_name = 'quantity_of_requests_to_gpt4_bing'
        else:
            table_name = 'quantity_of_requests_to_gpt3'
        available_amount_of_requests = await get_available_amount_of_requests_to_chat_gpt(has_pro, selected_model,
                                                                                            has_working_bots,
                                                                                            amount_of_referrals)
        amount_of_requests = await get_amount_of_requests_for_user('./data/databases/quantity_of_requests.sqlite3', table_name,
                                                                    call.from_user.id)
        rest_of_requests = available_amount_of_requests - amount_of_requests
        message_text = f'✅ Вы выбрали модель: *{selected_model}*.\n\n'
        if rest_of_requests:
            message_text += f'⏳ Сегодня вы можете задать ей вопрос еще *{rest_of_requests} раз(а)*.'
            if has_pro:
                message_text += f'\n\n💎 Вы являетесь подписчиком ReshenijaBot PRO, поэтому ваш увеличенный лимит для выбранной модели составляет {available_amount_of_requests} запросов в день.'
            else:
                message_text += f'\n\nℹ️ Ваш лимит для выбранной модели составляет {available_amount_of_requests} запросов в день.'
            await UserState.chat_gpt_writer.set()
            dictionary_used_in_this_function['text_get_for_chat_gpt'] = True
        else:
            message_text += f'❗️ Вы достигли дневного лимита в {available_amount_of_requests} запросов к выбранной модели. Она вновь сможет отвечать на ваши запросы завтра.'
            if not has_pro:
                users_data = await get_dictionary(str(call.from_user.id), bot_instance.bot_id, 1)
                has_working_bots = await get_has_working_bots(call.from_user.id, bot_instance.bot_id, users_data)
                amount_of_referrals = await get_amount_of_referrals(call.from_user.id, bot_instance.bot_id, users_data)
                message_text += f'\n\n 💯 Чтобы увеличить лимит до {await get_available_amount_of_requests_to_chat_gpt(True, selected_model, has_working_bots, amount_of_referrals)} запросов в день, подключите PRO подписку в личном кабинете.'
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_model_selection'))
        await try_edit_or_send_message(call.from_user.id, bot_instance.bot, bot_instance.bot_id, call.message.chat.id, message_text,
                                        dictionary_used_in_this_function['id_of_message_with_markup'], markup,
                                        'markdown')
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
    elif call.data == 'back_to_model_selection':
        dictionary_used_in_this_function['text_get_for_chat_gpt'] = False
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
        await chat_gpt_starter(call, bot_instance)
