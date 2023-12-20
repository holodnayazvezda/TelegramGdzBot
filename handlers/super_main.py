# импорты из файлов
from utils.advertisements.ads_database_worker import create_ads, change_ads_status, get_ads_data
from utils.advertisements.ads_status_to_text import ads_status_to_text, status_code_to_menu_text
from utils.async_process_runner import start as async_functions_process_starter
from utils.chatgpt.audio_to_text import audio_to_text
from utils.bot.basic_prints import *
from utils.bot.bot_token_worker import check_bot_token, get_bot_info
from utils.bot.bots_worker import update_or_create_bot_data, get_working_bots_tokens, delete_bot, isworking, start_or_stop_bot, \
    get_all_bots_tokens
from utils.chatgpt.chat_gpt_worker import ask_chat_gpt_and_return_answer
from utils.coder_and_decoder import decode_and_write
from data.config import (get_buttons_list_for_user, get_reply_markup_for_user, MAIN_COMMANDS,
                    get_available_amount_of_bookmarks, PRICES_FOR_ADS, PRICE_FOR_WATCH, PRICES_FOR_PREMIUM,
                    get_max_tokens_in_response_for_user, get_available_amount_of_requests_to_chat_gpt)
from utils.database.database_worker import get_information_from
from utils.advertisements.get_ads_orders_by_status_code import get_ads_orders_by_status_code
from utils.aiogram_functions_worker import *
from utils.payments.payment_database_worker import *
from utils.payments.payment_yoomoney_worker import *
from utils.pro.pro_subscription_worker import *
from utils.database.rebooter import reboot_daily_users
from utils.share.share_worker import save_shared_data, get_save_data_id, get_shared_data
from utils.string_validator import string_validator, contains_only_allowed_chars
from utils.users.users import is_new_user, active_now
from utils.text_worker import *
from utils.gdz.megaresheba_worker import get_solution_by_link_at_number
from utils.middleware.throttling_middleware import ThrottlingMiddleware
from utils.chatgpt.gpt4free_worker import *
from utils.ocr.image_worker import *
from utils.chatgpt.requests_counter import *
from utils.chatgpt.chat_gpt_users_worker import clear_history_of_requests

# импорты aiogram
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.exceptions import Unauthorized

# импорт telebot для отправки сообщений без асинхронного контекста
from telebot.apihelper import ApiTelegramException

# импорты других библиотек
import os
import subprocess
import time
from datetime import datetime
from math import ceil

# глобальная переменная задачи перебора пользователей
on_processing_chat_gpt_users = False
# глобальная переменная для хранения текстов пользовательских сообщений и их id (chat gpt)
chats_ids_and_messages_for_chat_gpt_users = {}
on_processing_chat_gpt_pro_users = False
chats_ids_and_messages_for_chat_gpt_pro_users = {}
# глобальная переменная для перебора рекламных объявлений
on_processing_advertisements_payments = False


# класс для хранилища данных
class UserState(StatesGroup):
    find_solution = State()
    chat_gpt_writer = State()
    chat_gpt_worker = State()
    bookmark_creation = State()
    bookmark_working = State()
    bookmark_opening = State()
    my_account = State()
    new_bot_creation = State()
    advertisement_cabinet = State()
    advertisement_watching = State()
    manage_advertisements = State()
    on_ads_text_getting = State()
    for_developers = State()
    ads_buying = State()
    on_pro = State()
    on_gifting_pro = State()
    on_unsubscribing_pro = State()


tokens = {}


async def stop_bot(bot_token):
    try:
        tokens[bot_token]['thread'].join(0.01)
        tokens[bot_token]['dp'].stop_polling()
    except Exception:
        pass


async def start_bot(dp, bot_token):
    while dp.is_polling():
        pass
    while True:
        try:
            await dp.skip_updates()
            await dp.start_polling(error_sleep=3, relax=0.08)
            break
        except Unauthorized:
            await start_or_stop_bot(bot_token, False)
            Thread(target=async_functions_process_starter, args=(stop_bot, [bot_token])).start()
            break
        except Exception:
            await asyncio.sleep(7)


async def skip_updates_and_start_bot(dp, bot_token):
    if len(working_bots_tokens) > 1:
        event_loop.create_task(start_bot(dp, bot_token))
    elif len(working_bots_tokens) == 1:
        Thread(target=async_functions_process_starter, args=(start_bot, [dp, bot_token])).start()


def bot_init(token):
    global on_processing_advertisements_payments
    bot = Bot(token=token)
    bot_telebot = TeleBot(token=token, parse_mode=None)
    memory = MemoryStorage()
    dp = Dispatcher(bot, storage=memory)
    dp.middleware.setup(ThrottlingMiddleware())
    bot_id = int(token.split(':')[0])
    tokens[token] = {'dp': dp, 'thread': None, 'bot': bot}

    # handler отвечающий за нажатие кнопки "старт" или комманды '/start'
    @dp.message_handler(state='*', commands=['start'])
    async def start(message: types.Message):
        if '/start' in message.text and len(message.text.split()) > 1:
            if message.text.split()[1].isdigit():
                referral_user_id = int(message.text.split()[1])
                if referral_user_id != message.from_user.id and await is_new_user(str(message.from_user.id)) and not \
                        await is_new_user(str(referral_user_id)):
                    users_data = await get_dictionary(str(referral_user_id), bot_id, 1)
                    if 'referral_users' in users_data:
                        users_data['referral_users'].add(message.from_user.id)
                    else:
                        users_data['referral_users'] = set()
                        users_data['referral_users'].add(message.from_user.id)
                    await create_or_dump_user(str(referral_user_id), bot_id, str(users_data), 1)
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
                    await bot.send_message(message.chat.id, text='🟢', reply_markup=back_to_main_menu_markup)
                    await gdz_main_function(call, data_dict['all_data'])
                    return
        await UserState.find_solution.set()
        conversation_id = None
        try:
            dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
            if 'id_of_block_of_photos_send_by_bot' in dictionary_used_in_this_function and \
                    dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
                for id in dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
                    try:
                        await bot.delete_message(message.chat.id, id)
                    except Exception:
                        pass
            if 'chat_gpt_conversation_id' in dictionary_used_in_this_function:
                conversation_id = dictionary_used_in_this_function['chat_gpt_conversation_id']
            try:
                await bot.delete_message(message.chat.id, dictionary_used_in_this_function['id_of_message_with_markup'])
            except Exception:
                pass
        except Exception:
            pass
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id,
                                  str({'id_of_block_of_photos_send_by_bot': [], 'id_of_messages_about_bookmarks': [],
                                       'chat_gpt_conversation_id': conversation_id}), 2])).start()
        Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
        try:
            await try_edit_or_send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                           chat_id=message.chat.id,
                                           text=await welcome_user(message),
                                           reply_markup=await get_reply_markup_for_user(message.from_user.id),
                                           parse_mode="markdown")
        except Unauthorized:
            print('err Unauthorized')

    # это функция начало гдз. Отсюда начнется первый выбор класса, первая печать InlineKeyboardButtonS
    async def gdz_starter(message):
        users_dict = await get_dictionary(str(message.from_user.id), bot_id, 2)
        if users_dict:
            if isinstance(message, types.Message):
                Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
                users_dict['avaliable_classes_and_links_at_it'] = list(
                    map(lambda el: el[0], await get_information_from('./data/databases/gdz.sqlite3', 'classes', 'name')))
                markup = types.InlineKeyboardMarkup(row_width=2)
                buttons = []
                for z in users_dict['avaliable_classes_and_links_at_it']:
                    buttons.append(types.InlineKeyboardButton(z, callback_data=z))
                markup.add(*buttons)
                message_id = await try_edit_or_send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                            chat_id=message.chat.id,
                                                            text='Выбери свой класс!', reply_markup=markup)
                users_dict['id_of_message_with_markup'] = message_id
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id),
                                                                                           bot_id, str(users_dict),
                                                                                           2])).start()
            elif isinstance(message, types.CallbackQuery):
                try:
                    call = message
                    Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
                    users_dict['avaliable_classes_and_links_at_it'] = list(
                        map(lambda el: el[0], await get_information_from('./data/databases/gdz.sqlite3', 'classes', 'name')))
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    buttons = []
                    for z in users_dict['avaliable_classes_and_links_at_it']:
                        buttons.append(types.InlineKeyboardButton(z, callback_data=z))
                    markup.add(*buttons)
                    await answer_callback_query(call, bot)
                    try:
                        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                    except Exception:
                        pass
                    message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                                chat_id=call.message.chat.id,
                                                                text='Выбери свой класс!', reply_markup=markup)
                    users_dict['id_of_message_with_markup'] = message_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id),
                                                                                               bot_id, str(users_dict),
                                                                                               2])).start()
                except Exception:
                    pass

    # это функция, отвечающая за формирование валидного словаря всех номеров
    async def producer(spisok, call):
        if not isinstance(spisok, dict):
            return spisok
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        if dictionary_used_in_this_function:
            dictionary_used_in_this_function['spisok_all_numbers'] = spisok
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            main_dict = {}
            amount_of_buttons = ceil(len(spisok) / 98)
            keys = list(spisok.keys())
            for i in range(amount_of_buttons):
                pre_main_dict = {}
                count = 0
                for number in keys:
                    count += 1
                    if count <= 98:
                        pre_main_dict[number] = spisok[number]
                    else:
                        keys = keys[count - 1:]
                        break
                title = list(pre_main_dict.keys())[0] + '-' + list(pre_main_dict.keys())[-1]
                main_dict[title] = pre_main_dict
            if len(main_dict) == 1:
                return spisok
            return main_dict

    async def buttons_validator(buttons):
        if len(buttons) > 98:
            buttons = buttons[:98]
        return buttons

    async def check_ads_message_buttons_call(call):
        if 'pass_moderation_' in call.data or 'reject_moderation_' in call.data:
            await pass_or_reject_moderation(call)
            return True
        elif 'create_ads' in call.data:
            try:
                await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception:
                pass
            await UserState.advertisement_watching.set()
            await buy_advertisements(call)
            return True
        elif 'ads_' in call.data:
            try:
                await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception:
                pass
            await UserState.manage_advertisements.set()
            call.data = int(call.data.split('_')[1])
            await view_ads_info(call)
            return True
        elif 'pay_' in call.data:
            try:
                await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception:
                pass
            await pay_ads(call)
            return True
        elif 'delete_this_message' in call.data:
            if '_and_go_to_my_account' in call.data:
                await my_account_starter(call)
            elif '_and_open_advertisement_cabinet' in call.data:
                await advertisement_cabinet(call)
            else:
                try:
                    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                except Exception:
                    pass
            return True
        return False

    # это handler, отвечающий за обработку всех Callback кнопок
    @dp.callback_query_handler(lambda call: True, state=UserState.find_solution)
    async def gdz_main_function(call: types.CallbackQuery, dictionary_to_use=None, state: FSMContext = None):
        if await check_ads_message_buttons_call(call):
            return
        if dictionary_to_use:
            dictionary_used_in_this_function = dictionary_to_use
        else:
            dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        if 'old_dict' not in dictionary_used_in_this_function:
            dictionary_used_in_this_function['old_dict'] = {}
        if 'id_of_messages_about_bookmarks' not in dictionary_used_in_this_function:
            dictionary_used_in_this_function['id_of_messages_about_bookmarks'] = []
        if dictionary_used_in_this_function['id_of_messages_about_bookmarks']:
            for id in dictionary_used_in_this_function['id_of_messages_about_bookmarks']:
                try:
                    await bot.delete_message(call.message.chat.id, id)
                except Exception:
                    pass
            dictionary_used_in_this_function['id_of_messages_about_bookmarks'] = []
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        if dictionary_used_in_this_function:
            Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
            try:
                if call.data == '⁉️ Найти решение':
                    await gdz_starter(call)
                elif 'двз' in call.data or 'share' in call.data:
                    # call.data = dictionary_used_in_this_function['current_key']
                    bookmark_dict = {'key': dictionary_used_in_this_function['current_key'],
                                     'all_data': dictionary_used_in_this_function}
                    if 'двз' in call.data:
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton(text='❌ отмена', callback_data=bookmark_dict['key']))
                        await answer_callback_query(call, bot)
                        if ('id_of_block_of_photos_send_by_bot' in dictionary_used_in_this_function and
                                dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']):
                            for id in dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
                                try:
                                    await bot.delete_message(call.message.chat.id, id)
                                except Exception:
                                    pass
                            dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                        try:
                            await bot.delete_message(chat_id=call.message.chat.id,
                                                     message_id=dictionary_used_in_this_function[
                                                         'id_of_message_with_markup'])
                        except Exception:
                            pass
                        dictionary_used_in_this_function['text_inputed'] = True
                        dictionary_used_in_this_function['bookmark_dict'] = bookmark_dict
                        message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                                    chat_id=call.message.chat.id,
                                                                    text='⬇️ Введите имя закладки',
                                                                    reply_markup=markup)
                        dictionary_used_in_this_function['id_of_messages_about_bookmarks'].append(
                            message_id)  # к этому моменту значение по этому ключу точно будет!
                        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                        # записать bookmark_dict в fsm
                        await UserState.bookmark_creation.set()
                        await state.update_data(bookmark_dict=bookmark_dict)
                        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                        # await main_function(call, dictionary_used_in_this_function)
                    else:
                        try:
                            last_message_text = call.message.md_text
                            if not last_message_text:
                                last_message_text = call.message.html_text
                            if not last_message_text:
                                last_message_text = call.message.text
                            if not last_message_text:
                                last_message_text = ''
                            if last_message_text and 'Поделись' in last_message_text and 'чтобы получить быстрый доступ к выбранному учебнику' in last_message_text:
                                try:
                                    await bot.answer_callback_query(call.id, "Скопируй ссылку из сообщения!")
                                except Exception:
                                    pass
                            else:
                                data_name = call.data.split("$")[1]
                                type_of_data = int(call.data.split("$")[2])  # 1 - книга, 2 - номер
                                id, success = await get_save_data_id(data_name, './data/databases/shared_data.sqlite3', "shared_data_ids")
                                if not success:
                                    id = await save_shared_data(data_name, bookmark_dict, './data/databases/shared_data.sqlite3', 'shared_data')
                                link = f'https://t.me/{(await bot.get_me()).username}?start=shared_data{id}'
                                if type_of_data == 1:
                                    await call.message.edit_caption(last_message_text + f'\n\n🔗 Поделись *этой ссылкой*, чтобы получить быстрый доступ к выбранному учебнику (номеру): `{link}`', parse_mode='markdown', reply_markup=call.message.reply_markup)
                                else:
                                    await call.message.edit_text(last_message_text + f'\n\n🔗 Поделись *этой ссылкой*, чтобы получить быстрый доступ к выбранному учебнику (номеру): `{link}`', parse_mode='markdown', reply_markup=call.message.reply_markup)
                        except Exception as e:
                            print(e)
                            try:
                                await bot.answer_callback_query(call.id, "Непредвиденная ошибка! Попробуйте еще раз или поделитесь следующим номером")
                            except Exception:
                                pass
                elif call.data == 'bookmarks':
                    await get_bookmarks(call)
                elif call.data in dictionary_used_in_this_function['avaliable_classes_and_links_at_it']:
                    try:
                        dictionary_used_in_this_function[
                            'current_state_of_main_dict'] = 'avaliable_classes_and_links_at_it'
                        dictionary_used_in_this_function['current_key'] = call.data
                        dictionary_used_in_this_function['clas'] = call.data
                        dictionary_used_in_this_function['subjects_and_links'] = list(
                            map(lambda el: el[0],
                                await get_information_from('./data/databases/gdz.sqlite3', 'subjects', 'name', call.data)))
                        markup = types.InlineKeyboardMarkup(row_width=2)
                        buttons = []
                        for i in dictionary_used_in_this_function['subjects_and_links']:
                            buttons.append(types.InlineKeyboardButton(i, callback_data=i))
                        markup.add(*await buttons_validator(buttons))
                        markup.add(types.InlineKeyboardButton('📌 Добавить в закладки', callback_data=f'двз'))
                        markup.add(types.InlineKeyboardButton('⏪ Назад', callback_data='⁉️ Найти решение'))
                        await answer_callback_query(call, bot)
                        message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                                    chat_id=call.message.chat.id,
                                                                    text=f'Выбери нужный предмет за {" ".join(dictionary_used_in_this_function["clas"].split()[1:])}',
                                                                    message_id=call.message.message_id,
                                                                    reply_markup=markup)
                        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                    except Exception as e:
                        print(e)
                elif call.data in dictionary_used_in_this_function['subjects_and_links']:
                    try:
                        dictionary_used_in_this_function['current_state_of_main_dict'] = 'subjects_and_links'
                        dictionary_used_in_this_function['current_key'] = call.data
                        dictionary_used_in_this_function['subject'] = call.data
                        dictionary_used_in_this_function['dict_of_authors_and_links'] = \
                            list(map(lambda el: el[0],
                                     await get_information_from('./data/databases/gdz.sqlite3', 'authors', 'name',
                                                                dictionary_used_in_this_function['clas'] + '-' + call.
                                                                data)))
                        markup = types.InlineKeyboardMarkup(row_width=2)
                        buttons = []
                        for element in await buttons_validator(
                                dictionary_used_in_this_function['dict_of_authors_and_links']):
                            buttons.append(types.InlineKeyboardButton(element, callback_data=element))
                        markup.add(*await buttons_validator(buttons))
                        markup.add(types.InlineKeyboardButton('📌 Добавить в закладки',
                                                              callback_data=f'двз'))
                        markup.add(
                            types.InlineKeyboardButton('⏪ Назад',
                                                       callback_data=dictionary_used_in_this_function['clas']))
                        await answer_callback_query(call, bot)
                        message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                                    chat_id=call.message.chat.id,
                                                                    text=f'Выбери автора твоей книги по выбранному предмету ({dictionary_used_in_this_function["subject"].lower()})',
                                                                    message_id=call.message.message_id,
                                                                    reply_markup=markup)
                        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                    except Exception as error:
                        print(f'Ошибка! {error}')
                elif call.data in dictionary_used_in_this_function['dict_of_authors_and_links']:
                    try:
                        dictionary_used_in_this_function['current_state_of_main_dict'] = 'dict_of_authors_and_links'
                        dictionary_used_in_this_function['current_key'] = call.data
                        dictionary_used_in_this_function['writer'] = call.data
                        dictionary_used_in_this_function['dict_of_different_books'] = {}
                        for word in list(
                                map(lambda el: el[0], await get_information_from('./data/databases/gdz.sqlite3', 'books', 'name',
                                                                                 dictionary_used_in_this_function[
                                                                                     'clas'] + '-' +
                                                                                 dictionary_used_in_this_function[
                                                                                     'subject'] + '-' + call.data))):
                            dictionary_used_in_this_function['dict_of_different_books'][word] = word + '.txt'
                        markup = types.InlineKeyboardMarkup(row_width=1)
                        buttons = []
                        to_add = list(dictionary_used_in_this_function['dict_of_different_books'].keys())
                        for element in to_add:
                            buttons.append(types.InlineKeyboardButton(text=element, callback_data=element))
                        markup.add(*await buttons_validator(buttons))
                        markup.add(types.InlineKeyboardButton('📌 Добавить в закладки',
                                                              callback_data=f'двз'))
                        markup.add(types.InlineKeyboardButton(text='⏪ Назад',
                                                              callback_data=dictionary_used_in_this_function[
                                                                  'subject']))
                        await answer_callback_query(call, bot)
                        message_id = await send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id,
                                                        text=f'Выбери тип твоей книги по выбранному предмету ({dictionary_used_in_this_function["subject"].lower()})',
                                                        message_id=call.message.message_id, reply_markup=markup)
                        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                    except Exception:
                        pass
                elif call.data in dictionary_used_in_this_function['dict_of_different_books']:
                    try:
                        dictionary_used_in_this_function['current_state_of_main_dict'] = 'dict_of_different_books'
                        dictionary_used_in_this_function['current_key'] = call.data
                        dictionary_used_in_this_function['typ'] = call.data
                        dictionary_used_in_this_function['activity'] = []
                        book_name = f"/{dictionary_used_in_this_function['clas']}/{dictionary_used_in_this_function['subject']}/{dictionary_used_in_this_function['writer']}/{dictionary_used_in_this_function['typ']}"
                        res = await get_information_from('./data/databases/gdz.sqlite3', 'books_data', 'name',
                                                         dictionary_used_in_this_function['clas'] + '-' +
                                                         dictionary_used_in_this_function['subject'] + '-' +
                                                         dictionary_used_in_this_function['writer'] + '-' + call.data)
                        try:
                            dictionary_used_in_this_function['dict'] = eval(res[0][0])
                        except Exception:
                            dictionary_used_in_this_function['dict'] = res
                        if dictionary_used_in_this_function['dict']:
                            markup = types.InlineKeyboardMarkup()
                            tasks_data = {}
                            for data in dictionary_used_in_this_function['dict']['data']:
                                if not data:
                                    tasks_data['Упражнения'] = dictionary_used_in_this_function['dict']['data'][data]
                                else:
                                    tasks_data[data] = dictionary_used_in_this_function['dict']['data'][data]
                            dictionary_used_in_this_function['dict']['data'] = tasks_data
                            for element in await buttons_validator(
                                    list(tasks_data.keys())):
                                markup.add(types.InlineKeyboardButton(text=element, callback_data=element))
                            markup.add(types.InlineKeyboardButton('📌 Добавить в закладки',
                                                                  callback_data=f'двз'))
                            markup.add(types.InlineKeyboardButton(text='🔗 Поделиться решением',
                                                                  callback_data=f'share${book_name.__hash__()}$1'))
                            markup.add(types.InlineKeyboardButton(text='⏪ Назад',
                                                                  callback_data=dictionary_used_in_this_function[
                                                                      'writer']))
                            await answer_callback_query(call, bot)
                            photo = await decode_and_write(dictionary_used_in_this_function['dict']['img'])
                            if dictionary_used_in_this_function['dict']['country'] is not None:
                                if dictionary_used_in_this_function['dict']['country'] == 'ru':
                                    country = '🇷🇺 Россия'
                                elif dictionary_used_in_this_function['dict']['country'] == 'by':
                                    country = '🇧🇾 Беларусь'
                                elif dictionary_used_in_this_function['dict']['country'] == 'kz':
                                    country = '🇰🇿 Казахстан'
                                elif dictionary_used_in_this_function['dict']['country'] == 'kg':
                                    country = '🇰🇬 Киргизия'
                                else:
                                    country = 'Украина'
                            else:
                                country = None
                            caption = f"Название: *{dictionary_used_in_this_function['dict']['full name']}*"
                            if country:
                                caption += f"\n\nСтрана: *{country}*"
                            if dictionary_used_in_this_function['dict']['authors'] is not None:
                                caption += f"\nАвторы: *{dictionary_used_in_this_function['dict']['authors']}*"
                            if dictionary_used_in_this_function['dict']['publisher'] is not None:
                                caption += f"\nИздательство: *{dictionary_used_in_this_function['dict']['publisher']}*"
                            if dictionary_used_in_this_function['dict']['series'] is not None:
                                caption += f"\nТип: *{dictionary_used_in_this_function['dict']['series']}*"
                            caption += '\n\nВыбери, в каком разделе находятся твои задания'
                            message_id = await send_photo(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                          chat_id=call.message.chat.id, photo=photo, caption=caption,
                                                          message_id=call.message.message_id, reply_markup=markup,
                                                          parse_mode='markdown')
                            dictionary_used_in_this_function['dict'] = dictionary_used_in_this_function['dict']['data']
                            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                        else:
                            markup = types.InlineKeyboardMarkup()
                            markup.add(types.InlineKeyboardButton(text='⏪ Назад',
                                                                  callback_data=dictionary_used_in_this_function[
                                                                      'writer']))
                            try:
                                x = await bot.edit_message_text(chat_id=call.message.chat.id,
                                                                message_id=call.message.message_id,
                                                                text='🛑 Нам не удалось получить данные для выбранного решебника, рекомендуем посетить сайт https://megaresheba.ru для поиска решений номеров этого учебника',
                                                                reply_markup=markup)
                                dictionary_used_in_this_function['id_of_message_with_markup'] = x.message_id
                            except MessageNotModified:
                                pass
                            except Exception:
                                try:
                                    await bot.delete_message(call.message.chat.id, call.message.message_id)
                                except Exception:
                                    pass
                                x = await bot.send_message(chat_id=call.message.chat.id,
                                                           text='🛑 Нам не удалось получить данные для выбранного решебника, рекомендуем посетить сайт https://megaresheba.ru для поиска решений номеров этого учебника.',
                                                           reply_markup=markup)
                                dictionary_used_in_this_function['id_of_message_with_markup'] = x.message_id
                        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                    except Exception as error:
                        print(error)
                elif call.data in dictionary_used_in_this_function['dict'] or \
                        call.data in dictionary_used_in_this_function['old_dict']:
                    if call.data in dictionary_used_in_this_function['old_dict']:
                        dictionary_used_in_this_function['dict'] = dictionary_used_in_this_function['old_dict']
                        dictionary_used_in_this_function['old_dict'] = {}
                    try:
                        dictionary_used_in_this_function['current_state_of_main_dict'] = 'dict'
                        dictionary_used_in_this_function['current_key'] = call.data
                        to_check = await producer(dictionary_used_in_this_function['dict'][call.data], call)
                        dictionary_used_in_this_function['spisok_all_numbers'] = \
                            dictionary_used_in_this_function['dict'][
                                call.data]
                        try:
                            dictionary_used_in_this_function['activity'].append(call.data)
                        except Exception:
                            dictionary_used_in_this_function['activity'] = [call.data]
                        if to_check:
                            markup = types.InlineKeyboardMarkup(row_width=4)
                            elements = list(to_check.keys())
                            buttons = []
                            for element in elements:
                                buttons.append(types.InlineKeyboardButton(text=element, callback_data=element))
                            markup.add(*await buttons_validator(buttons))
                            markup.add(types.InlineKeyboardButton('📌 Добавить в закладки',
                                                                  callback_data=f'двз'))
                            if len(dictionary_used_in_this_function['activity']) != len(
                                    set(dictionary_used_in_this_function['activity'])):
                                dictionary_used_in_this_function['activity'] = dictionary_used_in_this_function[
                                                                                   'activity'][
                                                                               :dictionary_used_in_this_function[
                                                                                    'activity'].index(call.data) + 1]
                            try:
                                back_key = dictionary_used_in_this_function['activity'][-2]
                            except Exception:
                                back_key = dictionary_used_in_this_function['typ']
                            markup.add(types.InlineKeyboardButton(text='⏪ Назад',
                                                                  callback_data=back_key))
                            if ('id_of_block_of_photos_send_by_bot' in dictionary_used_in_this_function and
                                    dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']):
                                for id in dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
                                    try:
                                        await bot.delete_message(call.message.chat.id, id)
                                    except Exception:
                                        pass
                                dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                            try:
                                try:
                                    await bot.delete_message(call.message.chat.id, call.message.message_id)
                                except Exception:
                                    pass
                                await answer_callback_query(call, bot)
                                message_id = \
                                    await send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                       chat_id=call.message.chat.id,
                                                       text='Наконец, выбери нужный(ую) номер / страницу / параграф / раздел',
                                                       reply_markup=markup)
                                dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                                check_key = list(to_check.values())[0]
                                if not isinstance(check_key, str):
                                    dictionary_used_in_this_function['old_dict'] = dictionary_used_in_this_function[
                                        'dict']
                                    dictionary_used_in_this_function['dict'] = to_check
                                else:
                                    if check_key.count('-') < 4 and not check_key.lower().startswith('гдз   '):
                                        dictionary_used_in_this_function['old_dict'] = dictionary_used_in_this_function[
                                            'dict']
                                        dictionary_used_in_this_function['dict'] = to_check
                                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                            except Exception:
                                pass
                        else:
                            markup = types.InlineKeyboardMarkup(row_width=1)
                            markup.add(
                                types.InlineKeyboardButton(text='⏪ Назад',
                                                           callback_data=dictionary_used_in_this_function['typ']))
                            if ('id_of_block_of_photos_send_by_bot' in dictionary_used_in_this_function and
                                    dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']):
                                for id in dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
                                    try:
                                        await bot.delete_message(call.message.chat.id, id)
                                    except Exception:
                                        pass
                                dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                            try:
                                try:
                                    await bot.delete_message(call.message.chat.id, call.message.message_id)
                                except Exception:
                                    pass
                                await answer_callback_query(call, bot)
                                x = await bot.send_message(chat_id=call.message.chat.id,
                                                           text='К сожалению, мы не можем получить информацию для этого учебника, скорее всего он доступен только по подписке ;(',
                                                           reply_markup=markup)
                                dictionary_used_in_this_function['id_of_message_with_markup'] = x.message_id
                                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                            except Exception:
                                pass
                    except Exception as error:
                        print(error)
                elif call.data in dictionary_used_in_this_function['spisok_all_numbers']:
                    dictionary_used_in_this_function['current_state_of_main_dict'] = 'spisok_all_numbers'
                    dictionary_used_in_this_function['current_key'] = call.data
                    dictionary_used_in_this_function['number'] = call.data
                    number_name = f"/{dictionary_used_in_this_function['clas']}/{dictionary_used_in_this_function['subject']}/{dictionary_used_in_this_function['writer']}/{dictionary_used_in_this_function['typ']}"
                    for i in dictionary_used_in_this_function['activity']:
                        number_name += f'/{i}'
                    number_name = f"{number_name}/{dictionary_used_in_this_function['current_key']}"
                    link_at_number_data = dictionary_used_in_this_function['spisok_all_numbers'][
                        dictionary_used_in_this_function['number']]
                    try:
                        dct = await get_information_from("./data/databases/gdz.sqlite3", 'numbers_data', 'name',
                                                         link_at_number_data)
                        link_at_number = dct[0][0]
                        solution_data = await get_solution_by_link_at_number(link_at_number)
                        if solution_data['type'] == 0 or len(solution_data['data']) == 0:
                            raise Exception
                        markup = types.InlineKeyboardMarkup()
                        buttons = []
                        if len(dictionary_used_in_this_function['spisok_all_numbers']) > 1:
                            back_number = list(dictionary_used_in_this_function['spisok_all_numbers'].keys())[
                                list(dictionary_used_in_this_function['spisok_all_numbers'].keys()).index(
                                    dictionary_used_in_this_function['number']) - 1]
                            buttons.append(
                                types.InlineKeyboardButton(text=f'◀ {back_number}', callback_data=back_number))
                            try:
                                next_number = list(dictionary_used_in_this_function['spisok_all_numbers'].keys())[
                                    list(dictionary_used_in_this_function['spisok_all_numbers'].keys()).index(
                                        dictionary_used_in_this_function['number']) + 1]
                            except IndexError:
                                next_number = list(dictionary_used_in_this_function['spisok_all_numbers'].keys())[0]
                            buttons.append(
                                types.InlineKeyboardButton(text=f'{next_number} ▶', callback_data=next_number))
                            markup.add(*await buttons_validator(buttons))
                        markup.add(types.InlineKeyboardButton(text='Фото номера {} на megaresheba (источник)'.format(
                            dictionary_used_in_this_function['number']),
                            url=link_at_number))
                        markup.add(types.InlineKeyboardButton('📌 Добавить в закладки',
                                                              callback_data='двз'))
                        markup.add(types.InlineKeyboardButton(text='🔗 Поделиться решением', callback_data=f'share${number_name.__hash__()}$2'))
                        if isinstance(dictionary_used_in_this_function['activity'], str):
                            dictionary_used_in_this_function['activity'] = [
                                dictionary_used_in_this_function['activity']]
                        markup.add(types.InlineKeyboardButton('⏪ Назад', callback_data=dictionary_used_in_this_function[
                            'activity'][-1]))
                        if ('id_of_block_of_photos_send_by_bot' in dictionary_used_in_this_function and
                                dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']):
                            for id in dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
                                try:
                                    await bot.delete_message(call.message.chat.id, id)
                                except Exception:
                                    pass
                            dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                        try:
                            await bot.delete_message(call.message.chat.id, call.message.message_id)
                        except Exception:
                            pass
                        await answer_callback_query(call, bot)
                        if solution_data['type'] == 1:
                            images = []
                            for image in solution_data['data'][:10]:
                                images.append(types.InputMediaPhoto(media=image, parse_mode='html'))
                            z = await bot.send_media_group(chat_id=call.message.chat.id, media=images)
                            dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'].extend(
                                list(map(lambda el: el.message_id, z)))
                            if len(solution_data['data']) > 10:
                                if (not dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] or
                                        not isinstance(dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'], list)):
                                    dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                                for image in solution_data['data'][10:]:
                                    message_id = await send_photo(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                                  chat_id=call.message.chat.id, photo=image,
                                                                  parse_mode="html", do_not_add_ads=True)
                                    dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'].append(message_id)
                            if solution_data['task']:
                                message_text = f'📷 Фото запрашиваемого [задания ({dictionary_used_in_this_function["number"]})]({link_at_number}).\n📖 Текст задания: `{solution_data["task"]}`\n\nИсточник: https://megaresheba.ru'
                            else:
                                message_text = f'📷 Фото запрашиваемого [задания ({dictionary_used_in_this_function["number"]})]({link_at_number}).\n\nИсточник: https://megaresheba.ru'
                            message_id = await send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                            chat_id=call.message.chat.id,
                                                            text=message_text,
                                                            reply_markup=markup, parse_mode='markdown')
                        else:
                            if solution_data['task']:
                                message_text = f'📷 Ответ на запрашиваемое [задание ({dictionary_used_in_this_function["number"]})]({link_at_number}).\n📖 Текст задания: `{solution_data["task"]}`\n*{solution_data["data"]}*\n\nИсточник: https://megaresheba.ru'
                            else:
                                message_text = f'📷 Ответ на запрашиваемое [задание ({dictionary_used_in_this_function["number"]})]({link_at_number}).\n*{solution_data["data"]}*\nИсточник: https://megaresheba.ru'
                            message_id = await send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                            chat_id=call.message.chat.id,
                                                            text=message_text,
                                                            reply_markup=markup, parse_mode='markdown')
                        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                    except Exception:
                        link_at_number = await get_information_from("./data/databases/gdz.sqlite3", 'numbers_data', 'name',
                                                                    link_at_number_data)
                        markup = types.InlineKeyboardMarkup()
                        buttons = []
                        if len(dictionary_used_in_this_function['spisok_all_numbers']) > 1:
                            back_number = list(dictionary_used_in_this_function['spisok_all_numbers'].keys())[
                                list(dictionary_used_in_this_function['spisok_all_numbers'].keys()).index(
                                    dictionary_used_in_this_function['number']) - 1]
                            buttons.append(
                                types.InlineKeyboardButton(text=f'◀ {back_number}', callback_data=back_number))
                            try:
                                next_number = list(dictionary_used_in_this_function['spisok_all_numbers'].keys())[
                                    list(dictionary_used_in_this_function['spisok_all_numbers'].keys()).index(
                                        dictionary_used_in_this_function['number']) + 1]
                            except IndexError:
                                next_number = list(dictionary_used_in_this_function['spisok_all_numbers'].keys())[0]
                            buttons.append(
                                types.InlineKeyboardButton(text=f'{next_number} ▶', callback_data=next_number))
                            markup.add(*await buttons_validator(buttons))
                        markup.add(types.InlineKeyboardButton(
                            text='{} на сайте megaresheba'.format(dictionary_used_in_this_function['number']),
                            url=link_at_number[0][0]))
                        markup.add(types.InlineKeyboardButton('📌 Добавить в закладки',
                                                              callback_data='двз'))
                        markup.add(types.InlineKeyboardButton(text='А почему не отправляются ?',
                                                              callback_data='А почему не отправляются ?'))
                        if isinstance(dictionary_used_in_this_function['activity'], str):
                            dictionary_used_in_this_function['activity'] = [
                                dictionary_used_in_this_function['activity']]
                        markup.add(types.InlineKeyboardButton(text='⏪ Назад',
                                                              callback_data=dictionary_used_in_this_function['activity']
                                                              [-1]))
                        await answer_callback_query(call, bot)
                        message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                                    chat_id=call.message.chat.id,
                                                                    text=f'Перейди по ссылке и получи решение своего номера! ({link_at_number[0][0]})',
                                                                    message_id=call.message.message_id,
                                                                    reply_markup=markup)
                        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                elif call.data == 'А почему не отправляются ?':
                    try:
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton(text='⏪ Назад',
                                                              callback_data=dictionary_used_in_this_function['number']))
                        await answer_callback_query(call, bot)
                        message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                                    chat_id=call.message.chat.id,
                                                                    text='Если вы попали сюда, то либо произошла внутрення ошибка (вернитесь назад и повторите попытку), либо выбранный вами номер временно недоступен. В связи с этим, бот будет отпраялять вам ссылку, ведущую на сайт-источник. Перейдя по ней вы наудете решение на свой вопрос :) P.S. Создатель данного бота прилагает все усилия, для того, чтобы ускорить и упростить получения нужного ответа ! Если вы не можете получить фото нужного решения "на прямую" - это не моя вина!',
                                                                    message_id=call.message.message_id,
                                                                    reply_markup=markup)
                        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                    except Exception:
                        pass
                else:
                    print(f'Данные не найдены "{call.data}"')
            except Exception:
                pass

    async def unsuccessful_response_to_revchatgpt(chat_id, user_id, message_text):
        try:
            response = await ask_chat_gpt_temporary_api(message_text, user_id)
            if response:
                bot_message_text = f'⚠️ Возникли проблемы с получением ответа от основной системы. Это ответ резервного api, модель - *gpt-3.5-turbo*:\n\n{response}'
                send_message_by_telebot(user_id=user_id, bot_telebot=bot_telebot, bot_id=bot_id, chat_id=chat_id,
                                        text=bot_message_text,
                                        parse_mode='markdown')
            else:
                raise Exception('The answer is empty')
        except Exception as e:
            print(f'unsuccessful chat gpt api error! {e}')
            send_message_by_telebot(user_id=user_id, bot_telebot=bot_telebot, bot_id=bot_id, chat_id=chat_id,
                                    text='🛑 Возникла ошибка при получении ответа! Повторите попытку через несколько минут.')

    async def generate_and_send_answer(chat_id, user_id, message_text):
        bot_telebot.send_chat_action(chat_id=chat_id, action='typing')
        dictionary_used_in_this_function = await get_dictionary(str(user_id), bot_id, 2)
        try:
            try:
                model = dictionary_used_in_this_function['selected_model']
            except KeyError:
                model = 'gpt-3.5-turbo'
            if model == 'gpt-4-bing':
                response = await ask_chat_gpt_4(prompt=message_text, user_id=user_id)
            else:
                response = await ask_chat_gpt_and_return_answer(model, prompt=message_text, user_id=user_id)
            if response[1] == 200:
                send_message_by_telebot(user_id=user_id, bot_telebot=bot_telebot, bot_id=bot_id, chat_id=chat_id,
                                        text=response[0],
                                        parse_mode='markdown')
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(user_id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            else:
                if response[1] == 400:
                    send_message_by_telebot(user_id=user_id, bot_telebot=bot_telebot, bot_id=bot_id, chat_id=chat_id,
                                            text="⚠️ Ваш запрос слишком длинный! Пожалуйста, сократите запрос, что бы бот смог обработать его.",
                                            parse_mode='markdown')
                else:
                    await unsuccessful_response_to_revchatgpt(chat_id, user_id, message_text)
        except Exception:
            await unsuccessful_response_to_revchatgpt(chat_id, user_id, message_text)

    async def process_chat_gpt_users():
        global on_processing_chat_gpt_users, chats_ids_and_messages_for_chat_gpt_users
        while True:
            for chat_id, message_data in list(chats_ids_and_messages_for_chat_gpt_users.items()):
                del chats_ids_and_messages_for_chat_gpt_users[chat_id]
                await generate_and_send_answer(chat_id, message_data[0], message_data[1])
            if len(chats_ids_and_messages_for_chat_gpt_users) == 0:
                on_processing_chat_gpt_users = False
                return

    async def process_chat_gpt_pro_users():
        global on_processing_chat_gpt_pro_users, chats_ids_and_messages_for_chat_gpt_pro_users
        while True:
            for chat_id, message_data in list(chats_ids_and_messages_for_chat_gpt_pro_users.items()):
                del chats_ids_and_messages_for_chat_gpt_pro_users[chat_id]
                await generate_and_send_answer(chat_id, message_data[0], message_data[1])
            if len(chats_ids_and_messages_for_chat_gpt_pro_users) == 0:
                on_processing_chat_gpt_pro_users = False
                return

    def delete_messages(delay, chat_id, users_message_id, bots_message_id):
        time.sleep(delay)
        try:
            bot_telebot.delete_message(chat_id=chat_id, message_id=users_message_id)
        except ApiTelegramException:
            pass
        if bots_message_id is not None:
            try:
                bot_telebot.delete_message(chat_id=chat_id, message_id=bots_message_id)
            except ApiTelegramException:
                pass

    async def translate_audio_to_text_and_start_generating(message, downloaded_message_file, has_pro, model):
        global on_processing_chat_gpt_users, chats_ids_and_messages_for_chat_gpt_users, \
            on_processing_chat_gpt_pro_users, chats_ids_and_messages_for_chat_gpt_pro_users
        voice_file_path_oga, voice_file_path_wav = None, None
        try:
            bot_telebot.send_chat_action(chat_id=message.chat.id, action='upload_voice')
            if message.voice.file_size / (1024 * 1024) > 5:
                raise Exception('The weight of the audiofile is more that 5M')
            if message.voice.duration > 90:
                raise Exception('The length of the audiofile is more that 90 seconds')
            voice_file_path_oga = os.path.abspath(downloaded_message_file.name)
            voice_file_path_wav = voice_file_path_oga.replace('.oga', '.wav')
            subprocess.run(['ffmpeg', '-i', voice_file_path_oga, voice_file_path_wav],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
            data = audio_to_text(voice_file_path_wav)
            chats_ids_and_messages_for_chat_gpt_pro_users[message.chat.id] = [message.from_user.id, data]
            try:
                os.remove(voice_file_path_oga)
            except Exception:
                pass
            try:
                os.remove(voice_file_path_wav)
            except Exception:
                pass
            if model == 'gpt-4-bing':
                if has_pro:
                    if on_processing_chat_gpt_pro_users is False:
                        on_processing_chat_gpt_pro_users = True
                        Thread(target=async_functions_process_starter, args=(process_chat_gpt_pro_users, [])).start()
                else:
                    if on_processing_chat_gpt_users is False:
                        on_processing_chat_gpt_users = True
                        Thread(target=async_functions_process_starter, args=(process_chat_gpt_users, [])).start()
            else:
                await generate_and_send_answer(message.chat.id, message.from_user.id, data)
        except Exception as e:
            if 'The length of the audiofile is more that 90 seconds' in str(e):
                message_text = '⚠️ Длинна голосового сообщения превышает 1.5 минуты! Оно не может быть обработано.'
            elif 'The weight of the audiofile is more that 5M' in str(e):
                message_text = \
                    '⚠️ Вес голосового сообщения не может превышать 5 мегабайт! Оно не может быть обработано.'
            else:
                message_text = '🛑 Не удалось распознать текст голосового сообщения, пожалуйста, попробуйте еще раз.'
            message_id = send_message_by_telebot(user_id=message.from_user.id, bot_telebot=bot_telebot,
                                                 bot_id=bot_id, chat_id=message.chat.id, text=message_text)
            if voice_file_path_oga:
                try:
                    os.remove(voice_file_path_oga)
                except Exception:
                    pass
            if voice_file_path_wav:
                try:
                    os.remove(voice_file_path_wav)
                except Exception:
                    pass
            Thread(target=delete_messages, args=(5, message.chat.id, message.message_id, message_id)).start()

    async def get_text_from_image_and_start_generating(message, filepath, model):
        global on_processing_chat_gpt_users, chats_ids_and_messages_for_chat_gpt_users, \
            on_processing_chat_gpt_pro_users, chats_ids_and_messages_for_chat_gpt_pro_users
        amount_of_requests_to_ocr_api, amount_of_unsucessful_requests_to_ocr_api = await get_amount_of_requests_for_user(
            "./data/databases/quantity_of_requests.sqlite3", "quantity_of_requests_to_ocr_space",
            message.from_user.id), await get_amount_of_requests_for_user("./data/databases/quantity_of_requests.sqlite3",
                                                                         "quantity_of_unsuccessful_requests_to_ocr_space",
                                                                         message.from_user.id)
        has_pro = await is_pro(message.from_user.id)
        available_amount_of_requests_to_ocr_api = (50 if has_pro else 7) if str(message.from_user.id) not in ADMINS \
            else 1000
        if (amount_of_requests_to_ocr_api < available_amount_of_requests_to_ocr_api and
                amount_of_unsucessful_requests_to_ocr_api < 35):
            bot_telebot.send_chat_action(chat_id=message.chat.id, action='upload_photo')
            image_url = f'https://api.telegram.org/file/bot{token}/{filepath}'
            data = await get_text_from_image(message.from_user.id, image_url, 15)
            if data:
                if model == 'gpt-4-bing':
                    if await is_pro(message.from_user.id):
                        chats_ids_and_messages_for_chat_gpt_pro_users[message.chat.id] = [message.from_user.id, data]
                        if on_processing_chat_gpt_pro_users is False:
                            on_processing_chat_gpt_pro_users = True
                            Thread(target=async_functions_process_starter, args=(process_chat_gpt_pro_users, [])).start()
                    else:
                        chats_ids_and_messages_for_chat_gpt_users[message.chat.id] = [message.from_user.id, data]
                        if on_processing_chat_gpt_users is False:
                            on_processing_chat_gpt_users = True
                            Thread(target=async_functions_process_starter, args=(process_chat_gpt_users, [])).start()
                else:
                    await generate_and_send_answer(message.chat.id, message.from_user.id, data)
            else:
                message_id = send_message_by_telebot(user_id=message.from_user.id, bot_telebot=bot_telebot,
                                                     bot_id=bot_id, chat_id=message.chat.id,
                                                     text='🛑 Не удалось распознать текст с изображения, пожалуйста, попробуйте отправить другое изображение.',
                                                     parse_mode='markdown')
                Thread(target=delete_messages, args=(5, message.chat.id, message.message_id, message_id)).start()
        else:
            if amount_of_requests_to_ocr_api <= available_amount_of_requests_to_ocr_api:
                message_text = f'❗️ К сожалению, вы достигли дневного лимита в {available_amount_of_requests_to_ocr_api} отправок изображений к ChatGPT. Вы вновь сможете отправить ChatGPT запрос изображением *после 00:00 по МСК*!'
                if not has_pro:
                    message_text = f'{message_text} 💯 Если вы хотите увеличить лимит до *50 запросов в день*, оформите подписку 💎 ReshenijaBot PRO! Вы можете это сделать в *личном кабинете*.'
                message_id = send_message_by_telebot(user_id=message.from_user.id, bot_telebot=bot_telebot,
                                                     bot_id=bot_id,
                                                     chat_id=message.chat.id,
                                                     text=message_text,
                                                     parse_mode='markdown')
            else:
                message_id = send_message_by_telebot(user_id=message.from_user.id, bot_telebot=bot_telebot,
                                                     bot_id=bot_id,
                                                     chat_id=message.chat.id,
                                                     text='⚠️ Количество ошибок при распознавании текста с изображений достигло 35. Попробуйте еще раз *после 00:00 по МСК*!',
                                                     parse_mode='markdown')
            Thread(target=delete_messages, args=(20, message.chat.id, message.message_id, message_id)).start()

    async def add_user_to_queue_and_start_generating(message):
        global on_processing_chat_gpt_users, chats_ids_and_messages_for_chat_gpt_users, \
            on_processing_chat_gpt_pro_users, chats_ids_and_messages_for_chat_gpt_pro_users
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        try:
            model = dictionary_used_in_this_function['selected_model']
        except KeyError:
            model = 'gpt-3.5-turbo'
        if model == 'gpt-4':
            table_name = 'quantity_of_requests_to_gpt4'
        elif model == 'gpt-4-bing':
            table_name = 'quantity_of_requests_to_gpt4_bing'
        else:
            table_name = 'quantity_of_requests_to_gpt3'
        has_pro = await is_pro(message.from_user.id)
        users_data = await get_dictionary(str(message.from_user.id), bot_id, 1)
        has_working_bots = await get_has_working_bots(message.from_user.id, bot_id, users_data)
        amount_of_referrals = await get_amount_of_referrals(message.from_user.id, bot_id, users_data)
        if (await get_amount_of_requests_for_user("./data/databases/quantity_of_requests.sqlite3", table_name, message.from_user.id) <
                await get_available_amount_of_requests_to_chat_gpt(has_pro, model, has_working_bots, amount_of_referrals)):
            if message.content_type == 'text':
                if model == 'gpt-4-bing':
                    if has_pro:
                        chats_ids_and_messages_for_chat_gpt_pro_users[message.chat.id] = [message.from_user.id,
                                                                                          message.text]
                        if on_processing_chat_gpt_pro_users is False:
                            on_processing_chat_gpt_pro_users = True
                            Thread(target=async_functions_process_starter, args=(process_chat_gpt_pro_users, [])).start()
                    else:
                        chats_ids_and_messages_for_chat_gpt_users[message.chat.id] = [message.from_user.id,
                                                                                      message.text]
                        if on_processing_chat_gpt_users is False:
                            on_processing_chat_gpt_users = True
                            Thread(target=async_functions_process_starter, args=(process_chat_gpt_users, [])).start()
                else:
                    await generate_and_send_answer(message.chat.id, message.from_user.id, message.text)
            elif message.content_type == 'voice':
                if has_pro:
                    try:
                        Thread(target=async_functions_process_starter,
                               args=(translate_audio_to_text_and_start_generating,
                                     [message, await (await message.voice.get_file()).download(), has_pro, model])).start()
                    except Exception:
                        pass
                else:
                    message_id = await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                    chat_id=message.chat.id,
                                                    text='⚠️ Функция отправки запроса Chat GPT голосовым сообщением доступна *только для подписчиков 💎 ReshenijaBot PRO*! Приобрести подписку вы можете в *личном кабинете*.',
                                                    parse_mode='markdown')
                    Thread(target=delete_messages, args=(7, message.chat.id, message.message_id, message_id)).start()
                    return
            elif message.content_type == 'photo':
                if message.media_group_id:
                    dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
                    if ('last_chat_gpt_photo_media' in dictionary_used_in_this_function and
                            message.media_group_id == dictionary_used_in_this_function['last_chat_gpt_photo_media']):
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        return
                    dictionary_used_in_this_function['last_chat_gpt_photo_media'] = message.media_group_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                try:
                    Thread(target=async_functions_process_starter,
                           args=(get_text_from_image_and_start_generating,
                                 [message, (await message.photo[-1].get_file()).file_path, model])).start()
                except Exception:
                    pass
        else:
            users_data = await get_dictionary(str(message.from_user.id), bot_id, 1)
            has_working_bots = await get_has_working_bots(message.from_user.id, bot_id, users_data)
            amount_of_referrals = await get_amount_of_referrals(message.from_user.id, bot_id, users_data)
            message_text = f'❗️ К сожалению, вы достигли *дневного лимита в {await get_available_amount_of_requests_to_chat_gpt(has_pro, model, has_working_bots, amount_of_referrals)} запросов к модели {model}*! Это ограничение необходимо для поддержания корректной работы и высокой скорости ответа бота. {model.capitalize()} снова сможет отвечать на ваши вопросы *после 00:00 по МСК*.'
            if not has_pro:
                message_text += '\n\n💯 Если вы хотите *увеличить лимит на количество запросов к Chat GPT*, оформите подписку 💎 ReshenijaBot PRO! Вы можете это сделать в *личном кабинете*.'
            message_id = await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                            chat_id=message.chat.id,
                                            text=message_text,
                                            parse_mode='markdown')
            Thread(target=delete_messages, args=(20, message.chat.id, message.message_id, message_id)).start()

    async def clear_chat_gpt_conversation(message):
        Thread(target=async_functions_process_starter, args=(clear_history_of_requests,
                                                             ['./data/databases/history_of_requests_to_chatgpt.sqlite3', 'users_history',
                                                              message.from_user.id])).start()
        await bot.send_message(chat_id=message.chat.id, text="✅ История диалога с ChatGPT очищена")

    @dp.message_handler(state=[UserState.chat_gpt_writer], content_types=['text', 'voice', 'photo'])
    async def chat_gpt_task_handler(message: types.Message):
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        if message.text == '↩ Назад в главное меню':
            await start(message)
        elif message.text == '🗑 Очистить историю диалога':
            await clear_chat_gpt_conversation(message)
        elif message.text == '/statistics':
            await statistics(message)
        elif message.text == '/bookmarks':
            await get_bookmarks(message)
        elif message.text == '/chat_gpt':
            await chat_gpt_starter(message)
        else:
            try:
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                await add_user_to_queue_and_start_generating(message)
            except Exception as e:
                print(e)
                try:
                    await bot.delete_message(message.chat.id, message.message_id)
                except Exception:
                    pass

    @dp.callback_query_handler(state=UserState.chat_gpt_writer)
    async def chat_gpt_inline_buttons_handler(call: types.CallbackQuery, state: FSMContext):
        if call.data == 'back_to_model_selection':
            dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
            dictionary_used_in_this_function['text_get_for_chat_gpt'] = False
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            await chat_gpt_starter(call)

    # это функция, отвечающая за обработку нажатия на 'найти решение'
    async def find_solution(message):
        Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
        back_to_main_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_to_main_menu_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
        await bot.send_message(message.chat.id, text='🟢', reply_markup=back_to_main_menu_markup)
        await gdz_starter(message)
        await UserState.find_solution.set()

    @dp.callback_query_handler(state=UserState.chat_gpt_worker)
    async def get_chat_gpt_version(call: types.CallbackQuery, state: FSMContext):
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        if 'gpt-' in call.data:
            users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
            has_working_bots = await get_has_working_bots(call.from_user.id, bot_id, users_data)
            amount_of_referrals = await get_amount_of_referrals(call.from_user.id, bot_id, users_data)
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
                    users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
                    has_working_bots = await get_has_working_bots(call.from_user.id, bot_id, users_data)
                    amount_of_referrals = await get_amount_of_referrals(call.from_user.id, bot_id, users_data)
                    message_text += f'\n\n 💯 Чтобы увеличить лимит до {await get_available_amount_of_requests_to_chat_gpt(True, selected_model, has_working_bots, amount_of_referrals)} запросов в день, подключите PRO подписку в личном кабинете.'
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_model_selection'))
            await try_edit_or_send_message(call.from_user.id, bot, bot_id, call.message.chat.id, message_text,
                                           dictionary_used_in_this_function['id_of_message_with_markup'], markup,
                                           'markdown')
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif call.data == 'back_to_model_selection':
            dictionary_used_in_this_function['text_get_for_chat_gpt'] = False
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            await chat_gpt_starter(call)

    @dp.message_handler(state=[UserState.chat_gpt_worker], content_types=['text'])
    async def chat_gpt_messages_handler(message: types.Message):
        if message.text == '↩ Назад в главное меню':
            await start(message)
        elif message.text == '🗑 Очистить историю диалога':
            await clear_chat_gpt_conversation(message)
        else:
            await generate_and_send_answer(message.chat.id, message.from_user.id, message.text)

    @dp.message_handler(state='*', commands=['chat_gpt'])
    async def chat_gpt_starter(message):
        if isinstance(message, types.Message):
            chat_id = message.chat.id
        else:
            chat_id = message.message.chat.id
        Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), chat_id, bot_id])).start()
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        text = '🤖 Привет, я *ИИ Сhat GPT*. Вы можете задавать мне вопросы, а я постараюсь ' \
               'максимально качественно на них ответить. Задавайте вопрос как можно точнее. От этого зависит точность ответа. ' \
               '\n\n✨ Вы можете спросить меня 3 способами:\n1) Отправив *текстовое сообщение*\n2) Отправив ' \
               '*изображение с заданием* (Это функция дорабатывается. Бот пока не распознает сложные математические ' \
               'выражения (дроби, квадратные уравнения и т.п.). *Не следует* пытаться решить их при помощи него.\n3) ' \
               'Отправив мне голосовое сообщение с вопросом (доступно с подпиской PRO).'
        has_pro = await is_pro(message.from_user.id)
        rest_of_amount_of_image_sending, amount_of_unsucessful_requests_to_ocr_api = (
            ((50 if has_pro else 7) if str(message.from_user.id) not in ADMINS else 1000) -
            (await get_amount_of_requests_for_user("./data/databases/quantity_of_requests.sqlite3", "quantity_of_requests_to_ocr_space",
                                                   message.from_user.id)),
            await get_amount_of_requests_for_user("./data/databases/quantity_of_requests.sqlite3",
                                                  "quantity_of_unsuccessful_requests_to_ocr_space",
                                                  message.from_user.id))
        if rest_of_amount_of_image_sending > 0 and amount_of_unsucessful_requests_to_ocr_api < 35:
            text += f'\n\n🖼 Сегодня вы можете отправлять мне изображения еще {rest_of_amount_of_image_sending} раз.'
        else:
            text += f'\n\n🖼 Вы вновь сможете отправлять мне изображения завтра.'
        text += f'\n\n🚀 Я поддерживаю две модели:\n1) *gpt-3.5-turbo - *самая популярная и доступная модель в семействе GPT, оптимизирована для чата и отлично справляется с пониманием и генерацией текста. Лимит токенов: {await get_max_tokens_in_response_for_user(has_pro)}.\n2) *gpt-4-bing* - одна из самых совершенных моделей в семействе ChatGPT, способна справляться со сложными и творческими задачами. Имеет *доступ в интернет* и *неограниченный объем* базы знаний. Идеально подойдет для написания сочинений, рефератов, и т.п. Лимит токенов: {await get_max_tokens_in_response_for_user(has_pro)}.\n\n*Лимит токенов* определяет макcимально возможную *длину вашего запроса*. 1 токен примерно равен 3 символам.'
        if has_pro:
            text += '\n\n💎 Поскольку вы являетесь подписчиком ReshenijaBot PRO, лимиты токенов удвоены.'
        text += '\n\nВыбери необходимую модель Chat GPT и задай свой вопрос!'
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text='gpt-3.5-turbo', callback_data='gpt-3.5-turbo'))
        markup.add(types.InlineKeyboardButton(text='gpt-4 (bing ai)', callback_data='gpt-4-bing'))
        if ('id_of_message_with_markup' not in dictionary_used_in_this_function or not
        dictionary_used_in_this_function['id_of_message_with_markup']):
            back_to_main_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            back_to_main_menu_markup.add(types.KeyboardButton(text='🗑 Очистить историю диалога'))
            back_to_main_menu_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
            await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id, chat_id=chat_id, text='🟢',
                               reply_markup=back_to_main_menu_markup, do_not_add_ads=True)
            message_id = await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                            chat_id=chat_id,
                                            text=text, reply_markup=markup, parse_mode='markdown')
        else:
            message_id = await try_edit_or_send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=chat_id,
                                                        text=text,
                                                        message_id=dictionary_used_in_this_function[
                                                            'id_of_message_with_markup'], reply_markup=markup,
                                                        parse_mode='markdown')
        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        await UserState.chat_gpt_worker.set()

    # это функция, отвечающая за открытие закладок
    @dp.message_handler(state='*', commands=['bookmarks'])
    async def get_bookmarks(message):
        if isinstance(message, types.Message):
            Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
        else:
            Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.message.chat.id, bot_id])).start()
        await UserState.bookmark_working.set()
        users_data = await get_dictionary(str(message.from_user.id), bot_id, 1)
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        try:
            try:
                await bot.delete_message(message.chat.id, dictionary_used_in_this_function['id_of_message_with_markup'])
            except Exception:
                pass
        except Exception:
            pass
        back_to_main_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_to_main_menu_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
        try:
            list_of_bookmarks = users_data['bookmarks']
        except KeyError:
            list_of_bookmarks = {}
        markup = types.InlineKeyboardMarkup(row_width=3)
        bookmarks_holder = []
        for bookmark in list_of_bookmarks:
            bookmarks_holder.append(types.InlineKeyboardButton(text=bookmark, callback_data=bookmark))
        markup.add(*bookmarks_holder)
        message_text = 'Выберите закладку, которую хотите открыть'
        if not len(bookmarks_holder):
            message_text = 'Пока вы не создали не одну закладку!'
        if isinstance(message, types.Message):
            chat_id = message.chat.id
            if message_text != 'Пока вы не создали не одну закладку!':
                await bot.send_message(chat_id, text='🟢', reply_markup=back_to_main_menu_markup)
            message_id = await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id, chat_id=chat_id,
                                            text=message_text, reply_markup=markup)
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        else:
            message_id = await try_edit_or_send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=message.message.chat.id, text=message_text,
                                                        message_id=message.message.message_id, reply_markup=markup)
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    @dp.callback_query_handler(state=UserState.bookmark_working)
    async def get_bookmark(call: types.CallbackQuery, state: FSMContext):
        if await check_ads_message_buttons_call(call):
            return
        try:
            Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
            users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
            dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
            dictionary_used_in_this_function['current_bookmark'] = call.data
            bookmark = users_data['bookmarks'][call.data]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text='Открыть закладку', callback_data='open_bookmark'))
            markup.add(types.InlineKeyboardButton(text='🗑 Удалить закладку', callback_data='delete_bookmark'))
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_bookmarks'))
            await UserState.bookmark_opening.set()
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id, text=f'Закладка: {call.data}',
                                                        message_id=call.message.message_id, reply_markup=markup)
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            await state.update_data(bookmark_dict=bookmark,
                                    bookmark_name=dictionary_used_in_this_function['current_bookmark'])
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        except Exception:
            pass

    @dp.callback_query_handler(state=UserState.bookmark_opening)
    async def bookmark_opening(call: types.CallbackQuery, state: FSMContext):
        if await check_ads_message_buttons_call(call):
            return
        try:
            data = await state.get_data()
            bookmark = data['bookmark_dict']
            bookmark_name = data['bookmark_name']
            Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
            if call.data == 'back_to_bookmarks':
                await get_bookmarks(call)
            elif call.data == 'delete_bookmark':
                users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
                dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
                try:
                    list_of_bookmarks = users_data['bookmarks']
                except KeyError:
                    list_of_bookmarks = {}
                del list_of_bookmarks[bookmark_name]
                users_data['bookmarks'] = list_of_bookmarks
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(users_data), 1])).start()
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(text='К списку всех закладок', callback_data='bookmarks'))
                message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                            chat_id=call.message.chat.id,
                                                            text='❌ Закладка успешно удалена',
                                                            message_id=call.message.message_id, reply_markup=markup)
                dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                await state.reset_state(with_data=True)
                await UserState.find_solution.set()
            elif call.data == 'open_bookmark':
                call.data = bookmark['key']
                await state.reset_state(with_data=True)
                await UserState.find_solution.set()
                await gdz_main_function(call, bookmark['all_data'])
            else:
                try:
                    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                                text='Произошла внутрення ошибка, для того, чтобы продолжить, '
                                                     'воспользуйтесь командой /start')
                except MessageNotModified:
                    pass
                except Exception:
                    await bot.send_message(chat_id=call.message.chat.id,
                                           text='Произошла внутрення ошибка, для того, чтобы продолжить, воспользуйтесь'
                                                ' командой /start')

        except Exception as error:
            await state.reset_state(with_data=True)
            await UserState.find_solution.set()
            print('Похоже, что пользователь ' + str(
                call.from_user.id) + ' спамит кнопками' + f' Возникла ошибка {error}')

    # handler, отвечающий за ввод имени закладки
    @dp.message_handler(state=UserState.bookmark_creation, content_types=['text'])
    async def get_name_of_bookmark(message: types.Message, state: FSMContext):
        Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        users_data = await get_dictionary(str(message.from_user.id), bot_id, 1)
        dictionary_used_in_this_function['id_of_messages_about_bookmarks'].append(message.message_id)
        data = await state.get_data()
        bookmark_name = await string_validator(message.text)
        bookmark_dict = data['bookmark_dict']
        try:
            bookmarks = users_data['bookmarks']
        except KeyError:
            bookmarks = {}
        markup = types.InlineKeyboardMarkup()
        try:
            markup.add(types.InlineKeyboardButton(text='🔎 Продолжить поиск', callback_data=bookmark_dict['key']))
        except Exception:
            print(f"Тут возникла ошибка: данные bookmark_dict: {bookmark_dict}")
        has_working_bots = await get_has_working_bots(message.from_user.id, bot_id, users_data)
        amount_of_referrals = await get_amount_of_referrals(message.from_user.id, bot_id, users_data)
        max_amount_of_bookmarks = await get_available_amount_of_bookmarks(message.from_user.id,
                                                                          'have_had_pro' in users_data,
                                                                          has_working_bots, amount_of_referrals)
        if len(bookmarks) >= max_amount_of_bookmarks:
            max_amount_of_bookmarks_message_text = \
                f'❗️ Вы достигли максимального количества закладок ({max_amount_of_bookmarks})!'
            if max_amount_of_bookmarks <= 99 - 16 and not has_working_bots:
                max_amount_of_bookmarks_message_text += f'\n\n_ℹ️ Если вы хотите увеличить максимальное количество закладок с_ *{max_amount_of_bookmarks}* _до_ *{max_amount_of_bookmarks + 15}* _штук, создайте своего бота на основе нашего движка @ReshenijaBot в меню_ *"👤 Мой аккаунт"*_. Вы также можете увеличить максимальное количество закладок путем приглашения пользователей в бота._ *Один приглашенный пользователь = +1 закладка*'
            elif max_amount_of_bookmarks <= 99 - 15 and not has_working_bots:
                max_amount_of_bookmarks_message_text += f'\n\n_ℹ️ Если вы хотите увеличить максимальное количество закладок с_ *{max_amount_of_bookmarks}* _до_ *{max_amount_of_bookmarks + 15}* _штук, создайте своего бота на основе нашего движка @ReshenijaBot в меню_ *"👤 Мой аккаунт"*'
            elif max_amount_of_bookmarks < 99:
                max_amount_of_bookmarks_message_text += f'\n\n_ℹ️ Вы также можете увеличить максимальное количество закладок путем приглашения пользователей в бота._ *Один приглашенный пользователь = +1 закладка*'
            message_id = await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                            chat_id=message.chat.id, text=max_amount_of_bookmarks_message_text,
                                            reply_markup=markup, parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        elif bookmark_name == '↩ Назад в главное меню' or bookmark_name in MAIN_COMMANDS:
            await command_handler(message, state)
        else:
            bookmarks[bookmark_name] = bookmark_dict
            try:
                users_data['bookmarks'] = bookmarks
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(users_data), 1])).start()
                dictionary_used_in_this_function['text_inputed'] = False
                dictionary_used_in_this_function['bookmark_dict'] = {}
                message_id = await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                chat_id=message.chat.id, text='✅ Закладка успешно добавлена!',
                                                reply_markup=markup)
                dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            except Exception:
                await bot.send_message(message.chat.id, text='Произошла ошибка!', reply_markup=markup)
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        await UserState.find_solution.set()
        await state.reset_state(with_data=True)

    async def my_account_starter(message):
        if isinstance(message, types.Message):
            chat_id = message.chat.id
        else:
            chat_id = message.message.chat.id
        Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), chat_id, bot_id])).start()
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text='🤖 Мои боты', callback_data='my_bots'))
        markup.add(types.InlineKeyboardButton(text='👥 Мои рефералы', callback_data='my_referrals'))
        has_pro = await is_pro(message.from_user.id)
        if not has_pro:
            markup.add(types.InlineKeyboardButton(text='⭐️ Купить PRO подписку', callback_data='buy_pro'))
        full_name = ''
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        if first_name:
            full_name += first_name
        if last_name:
            full_name += f' {last_name}'
        if not full_name:
            full_name = 'Anonymus'
        if has_pro:
            subscription_text = '✅ Активна'
            if (str(message.from_user.id) in ADMINS or (await get_amount_of_referrals(message.from_user.id, bot_id)) >=
                    AMOUNT_OF_REFERRALS_FOR_PRO):
                subscription_text += '\n⏳ Осталось: ♾'
            else:
                rest_of_pro = await get_the_rest_of_the_subscription_days(message.from_user.id)
                if rest_of_pro:
                    subscription_text += '\n⏳ Осталось'
                    if rest_of_pro[0]:
                        subscription_text += f" {await get_y_m_d_text({'y': rest_of_pro[0]})},"
                    if rest_of_pro[1]:
                        subscription_text += f" {await get_y_m_d_text({'m': rest_of_pro[1]})},"
                    if rest_of_pro[2]:
                        subscription_text += f" {await get_y_m_d_text({'d': rest_of_pro[2]})}"
                    else:
                        subscription_text += ' меньше дня'
        else:
            subscription_text = '❌ Не активна'
        account_message_text = \
            f"👤Вы: {full_name}\n🆔 Ваш *ID*: `{message.from_user.id}`\n\n💎 Подписка PRO: {subscription_text}"
        if isinstance(message, types.Message):
            message_id = await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                            chat_id=chat_id, text=account_message_text, reply_markup=markup,
                                            parse_mode='markdown')
        else:
            await answer_callback_query(message, bot)
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=chat_id, text=account_message_text,
                                                        message_id=id_of_message, reply_markup=markup,
                                                        parse_mode='markdown')
        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    @dp.callback_query_handler(lambda call: True, state=UserState.my_account)
    async def my_account_buttons_handler(call: types.CallbackQuery, state: FSMContext = FSMContext):
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        if await check_ads_message_buttons_call(call):
            return
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
        try:
            users_bots = users_data['bots']
        except (KeyError, TypeError):
            users_bots = {}
        if call.data == 'my_referrals':
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_my_account'))
            try:
                amount_of_referrals = len(users_data['referral_users'])
            except KeyError:
                amount_of_referrals = 0
            bots_username = (await bot.get_me()).username.replace('_', '\_')
            my_referrals_message_text = f'👥 Количество ваших рефералов: {amount_of_referrals}\n🔗 Ваша реферальна ссылка: https://t.me/{bots_username}?start={call.from_user.id}\n\n_ℹ️ За_ *каждого* _приглашенного пользователя вы получаете_ *+1* _запрос к модели ChatGPT gpt-4 и_ *+1* _закладку к лимиту на количество закладок_.\n\n💎 *Если вы пригласите {AMOUNT_OF_REFERRALS_FOR_PRO} и более человек, то получите подписку ReshenijaBot PRO навсегда!*'
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id, text=my_referrals_message_text,
                                                        message_id=call.message.message_id, reply_markup=markup,
                                                        parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif call.data == 'my_bots':
            dictionary_used_in_this_function['on_new_bot_creation'] = False
            markup = types.InlineKeyboardMarkup(row_width=2)
            for bot_token in users_bots:
                users_bot_info = await get_bot_info(bot_token)
                if None not in list(users_bot_info.values()):
                    users_bots[bot_token] = users_bot_info
                if bot_token == token:
                    bots_button_text = f"@{users_bots[bot_token]['username']} (этот бот)"
                else:
                    bots_button_text = f"@{users_bots[bot_token]['username']}"
                markup.add(types.InlineKeyboardButton(text=bots_button_text,
                                                      callback_data=bot_token))
            if len(users_bots) < 98:
                markup.add(types.InlineKeyboardButton(text='➕ Добавить бота', callback_data='add_bot'))
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_my_account'))
            if len(users_bots) == 0:
                my_bots_message_text = 'У вас пока нет ботов. Но вы можете создать его, нажав на кнопку ниже.\n\n_Подробно про то, как создать своего телеграм бота, вы можете прочесть_ [здесь](https://telegra.ph/Kak-sozdat-svoego-telegram-bota-i-podklyuchit-ego-k-dvizhku--ReshenijaBot-07-24).\n\n_ℹ️ За создание своего бота вы получаете удвоение количества запросов к модели ChatGPT gpt-4, а также увеличение лимита на количество закладок с 30 до 45 штук._'
            else:
                my_bots_message_text = f'🤖 Количество ваших ботов: *{len(users_bots)}* из *98*\n\n_Подробно про то, как создать своего телеграм бота, вы можете прочесть_ [здесь](https://telegra.ph/Kak-sozdat-svoego-telegram-bota-i-podklyuchit-ego-k-dvizhku--ReshenijaBot-07-24).\n\n_ℹ️ За создание своего бота вы получаете удвоение количества запросов к модели ChatGPT gpt-4, а также увеличение лимита на количество закладок с 30 до 45 штук._'
                if len(users_bots) >= 98:
                    my_bots_message_text += '\n\n_❕Вы создали максимальное количество ботов! Удалите одного из ранее созданных ботов, чтобы добавить нового_'
            await answer_callback_query(call, bot)
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id, text=my_bots_message_text,
                                                        message_id=id_of_message, reply_markup=markup,
                                                        parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(users_data), 1])).start()
        elif call.data == 'back_to_my_account':
            await UserState.my_account.set()
            await my_account_starter(call)
        elif call.data == 'add_bot':
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text='❌ Отмена', callback_data='my_bots'))
            message_text = f'⬇️ Отправьте в этот чат _токен_ своего бота.\n\n🗑 Через несколько секунд в целях безопасности ваш токен _будет_ удален из этого чата, а ваш бот будет подключен к движку 🤖 ReshenijaBot.\n\nВы можете создать *{98 - len(users_bots)}* ботов'
            await answer_callback_query(call, bot)
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id, text=message_text,
                                                        message_id=id_of_message, reply_markup=markup,
                                                        parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            await UserState.new_bot_creation.set()
            dictionary_used_in_this_function['on_new_bot_creation'] = True
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif call.data in users_bots:
            bot_token = call.data
            await show_bot_short_information(chat_id=call.message.chat.id, user_id=call.from_user.id,
                                             bot_token=bot_token)
        elif 'delete' in call.data:
            bot_token = '_'.join(call.data.split('_')[1:])
            markup = types.InlineKeyboardMarkup()
            markup.add(*[types.InlineKeyboardButton(text='✅ Да', callback_data=f'confirm_deletion_{bot_token}'),
                         types.InlineKeyboardButton(text='❌ Нет', callback_data=bot_token)])
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id,
                                                        text=f"Вы уверены, что хотите *удалить* бота *@{users_data['bots'][bot_token]['username']}*",
                                                        message_id=id_of_message, reply_markup=markup,
                                                        parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif 'stop' in call.data:
            bot_token = call.data.replace('stop_', '')
            if await isworking(bot_token, str(call.from_user.id)):
                await start_or_stop_bot(bot_token, False)
                await answer_callback_query(call=call, bot=bot, text='Бот остановлен', show_alert=True)
                Thread(target=async_functions_process_starter, args=(stop_bot, [bot_token])).start()
                await show_bot_short_information(call.message.chat.id, call.from_user.id, bot_token)
        elif 'start' in call.data:
            bot_token = call.data.replace('start_', '')
            if not await isworking(bot_token, str(call.from_user.id)):
                await start_or_stop_bot(bot_token, True)
                await answer_callback_query(call=call, bot=bot, text='Бот запущен', show_alert=True)
                bot_init(bot_token)
                await show_bot_short_information(call.message.chat.id, call.from_user.id, bot_token)
        elif 'confirm_deletion' in call.data:
            await answer_callback_query(call=call, bot=bot, text='Бот удален', show_alert=True)
            bot_token = call.data.replace('confirm_deletion_', '')
            if await isworking(bot_token, str(call.from_user.id)):
                await start_or_stop_bot(bot_token, False)
                Thread(target=async_functions_process_starter, args=(stop_bot, [bot_token])).start()
            await delete_bot(bot_token)
            del users_data['bots'][bot_token]
            call.data = 'my_bots'
            if not users_data['bots']:
                users_data['has_working_bots'] = False
            await create_or_dump_user(str(call.from_user.id), bot_id, str(users_data), 1)
            await my_account_buttons_handler(call, state)
        elif call.data == 'buy_pro':
            markup = types.InlineKeyboardMarkup()
            for month_text in PRICES_FOR_PREMIUM:
                markup.add(types.InlineKeyboardButton(text=f'{month_text} • {PRICES_FOR_PREMIUM[month_text]}₽',
                                                      callback_data=f'pro_{month_text}_{PRICES_FOR_PREMIUM[month_text]}'))
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_my_account'))
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id,
                                                        text=f"🆓 ReshenijaBot - это *бесплатный* сервис, помогающий тысячам школьником из разных стран. Благодаря рекламе он остается бесплатным. Если вы хотите *поддержать* этот сервис, а также *получить эксклюзивные функции*, оформите подписку PRO.\n\n💎 Подписка ReshenijaBot PRO *отключает рекламу в @ReshenijaBot*, а также рекламу во всех ботах ReshenijaBot движка. Помимо этого, она *дает доступ к эксклюзивным функциям*. Некоторые  из них:\n\n✅ Увеличение максимального количества закладок с *30* до *60* (Увеличивается *навсегда*. После окончания PRO подписки максимальное количество закладок *не будет* возвращено обратно к 30)\n✅ Увеличение лимита на количество запросов к модели ChatGPT *gpt-3.5-turbo*  (с *30* до *200* шт/день)\n✅ Увеличение лимита на количество запросов к модели ChatGPT с доступ в интернет *gpt-4-bing*  (с *3* до *50* шт/день)\n✅ Увеличение лимита на отправку запросов ChatGPT изображением (c *7* до *50* шт/день)\n✅ Высокая скорость работы ChatGPT, даже в период повышенной нагрузки.\n✅ Отправка запроса ChatGPT *голосовым сообщением*.",
                                                        message_id=id_of_message, reply_markup=markup,
                                                        parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            await UserState.on_pro.set()
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    async def check_payment_by_button(call: types.CallbackQuery, type_of_purchase):
        if await check_payment(call.data[6:]):
            if type_of_purchase == 1:
                try:
                    await change_ads_status(int(call.data[6:].split('_')[-1]), 4,
                                            {'bot_token': token, 'chat_id': call.message.chat.id}, True)
                except Exception:
                    pass
                await delete_payment(call.data[6:].split('_')[0])
                call.data = call.data[6:].split('_')[-1]
                await view_ads_info(call)
                await answer_callback_query(call=call, bot=bot,
                                            text='😃 Оплата прошла! Показ рекламного объявления запущен.',
                                            show_alert=True)
            else:
                await set_pro_for_user(call.from_user.id, int(call.data.split('_')[1]), call.message.chat.id,
                                       token)
                await delete_payment(call.data[6:], 2)
                await my_account_starter(call)
                await answer_callback_query(call=call, bot=bot,
                                            text='😃 Оплата прошла! Теперь реклама отключена, и вам доступны эксклюзивные функции!',
                                            show_alert=True)
        else:
            try:
                await answer_callback_query(call=call, bot=bot,
                                            text='🙁 Либо оплата не прошла, либо транзакция еще в пути.',
                                            show_alert=True)
            except Exception:
                pass

    @dp.callback_query_handler(lambda call: True, state=UserState.on_pro)
    async def buy_pro_buttons_handler(call: types.CallbackQuery, state: FSMContext):
        if await check_ads_message_buttons_call(call):
            return
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        if 'pro_' in call.data:
            global on_processing_advertisements_payments
            order_id = f"{call.from_user.id}_{call.data.split('_')[1].split()[0]}_{datetime.now()}"
            if str(call.from_user.id) in ADMINS or call.from_user.id == 5354767683:
                price = 2
            else:
                price = int(call.data.split('_')[-1])
            await add_payment(order_id, call.from_user.id, call.message.chat.id, token, 2)
            if not on_processing_advertisements_payments:
                on_processing_advertisements_payments = True
                Thread(target=async_functions_process_starter, args=(process_payments, [])).start()
            payment_link = await get_payment_link(order_id, price, 2)
            markup = types.InlineKeyboardMarkup()
            markup.add(*[types.InlineKeyboardButton(text=f"💳 Оплатить ({price}₽)", url=payment_link),
                         types.InlineKeyboardButton(text='🔄 Проверить',
                                                    callback_data=f'check-{order_id}')])
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data=f'buy_pro'))
            buy_pro_message_text = f'Чтобы приобрести подписку ReshenijaBot Pro на *{call.data.split("_")[1]}* и получить доступ к эксклюзивным функциям, оплатите [этот]({payment_link}) счет!\n\n❕ Если в течении минуты после оплаты бот не отправит вам сообщение о том, что оплата прошла, и вы являетесь подписчиком ReshenijaBot PRO, нажмите на кнопку *"🔄 Проверить"*. Если это не помогло, напишите нам в [поддержку](https://t.me/ReshenijaSupportBot).'
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                            chat_id=call.message.chat.id,
                                            text=buy_pro_message_text,
                                            message_id=id_of_message,
                                            reply_markup=markup, parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            users_data['id_of_pay_premium_message'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(users_data), 1])).start()
        elif call.data in ['buy_pro', 'back_to_my_account']:
            await my_account_buttons_handler(call, state)
        elif 'check' in call.data:
            await check_payment_by_button(call, 2)

    async def show_bot_short_information(chat_id, user_id, bot_token):
        dictionary_used_in_this_function = await get_dictionary(str(user_id), bot_id, 2)
        users_data = await get_dictionary(str(user_id), bot_id, 1)
        users_bot_info = await get_bot_info(bot_token)
        bot_online = False
        if None not in list(users_bot_info.values()):
            users_data['bots'][bot_token] = users_bot_info
            bot_online = True
        markup = types.InlineKeyboardMarkup()
        buttons = []
        if await isworking(bot_token, str(user_id)):
            status = '🟢 Запущен'
            buttons.append(types.InlineKeyboardButton(text='🔴 Остановить', callback_data=f'stop_{bot_token}'))
        else:
            status = '🔴 Остановлен'
            buttons.append(types.InlineKeyboardButton(text='🟢 Запустить', callback_data=f'start_{bot_token}'))
        buttons.append(types.InlineKeyboardButton(text='🗑 Удалить бота', callback_data=f'delete_{bot_token}'))
        markup.add(*buttons)
        markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='my_bots'))
        if bot_online:
            users_bot_message_text = f"🤖 Бот: *@{users_bot_info['username']}*\nCтатус: *{status}*\n\n*Имя*: {users_bot_info['name']}\n*Никнейм*: `@{users_bot_info['username']}`\nСсылка: `https://t.me/{users_bot_info['username']}`\n*ID*: {bot_token.split(':')[0]}\n\n*API Token*: `{bot_token}`"
        else:
            users_bot_message_text = f"🤖 Бот: *@{users_data['bots'][bot_token]['username']}*\nCтатус: *{status}*\n\n*Имя*: {users_data['bots'][bot_token]['name']}\n*Никнейм*: `@{users_data['bots'][bot_token]['username']}`\nСсылка: `https://t.me/{users_data['bots'][bot_token]['username']}`\n*ID*: {bot_token.split(':')[0]}\n\n*API Token*: `{bot_token}`\n\n‼️ Внимание! Нам не удалось получить актуальные данные об этом боте. Это могло произойти или из-за того, что вы удалили этого бота или изменили его токен, или из-за того, что этот бот был заблокирован!\n\n_P.S. Показанные выше данные этого бота могли устареть!_"
        if bot_token == token:
            users_bot_message_text += "\n\n❗️ Внимание! Сейчас вы находитесь в меню управления *ботом, с которым сейчас у вас открыт чат*! Остановка или удаление этого бота приведут к тому, что вы *не сможете* запустить его обратно из этого чата! (_То есть вы сможете это сделать только из другого бота, подключенного к движку @ReshenijaBot._)"
        if 'id_of_message_with_markup' in dictionary_used_in_this_function:
            id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
        else:
            id_of_message = None
        message_id = await try_edit_or_send_message(user_id=user_id, bot=bot, bot_id=bot_id, chat_id=chat_id,
                                                    text=users_bot_message_text, message_id=id_of_message,
                                                    reply_markup=markup, parse_mode='markdown')
        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(user_id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(user_id), bot_id, str(users_data), 1])).start()

    @dp.callback_query_handler(lambda call: True, state=UserState.new_bot_creation)
    async def new_bot_creation_cancellation_handler(call: types.CallbackQuery, state: FSMContext = None):
        if await check_ads_message_buttons_call(call):
            return
        await UserState.my_account.set()
        await my_account_buttons_handler(call, state)

    @dp.message_handler(state=UserState.new_bot_creation, content_types=['text'])
    async def new_bot_token_getting_handler(message: types.Message, state: FSMContext):
        if message.text == '↩ Назад в главное меню' or message.text in MAIN_COMMANDS:
            await command_handler(message, state)
        else:
            new_bot_token = message.text
            dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
            users_data = await get_dictionary(str(message.from_user.id), bot_id, 1)
            bots_info = await check_bot_token(new_bot_token)
            if bots_info['ok']:
                if new_bot_token not in await get_all_bots_tokens():
                    Thread(target=delete_messages, args=(1, message.chat.id, message.message_id, None)).start()
                    await update_or_create_bot_data(new_bot_token, str({'amount_of_unauthorized_errors': 0,
                                                                        'isworking': True}), str(message.from_user.id))
                    bot_init(new_bot_token)
                    users_data['has_working_bots'] = True
                    users_data['has_working_bots'] = True
                    if 'bots' not in users_data:
                        users_data['bots'] = {}
                    # Удалить цикл ниже, если в telegram API появится возможность изменять usernamе'ы ботов
                    for token in users_data['bots']:
                        if users_data['bots'][token]['username'] == bots_info['data']['username']:
                            del users_data['bots'][token]
                            break
                    if 'bots' in users_data:
                        users_data['bots'][new_bot_token] = bots_info['data']
                    else:
                        users_data['bots'] = {new_bot_token: bots_info['data']}
                    await UserState.my_account.set()
                    dictionary_used_in_this_function['on_new_bot_creation'] = False
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(users_data), 1])).start()
                    await show_bot_short_information(message.chat.id, message.from_user.id, new_bot_token)
                else:
                    x = await bot.send_message(chat_id=message.chat.id,
                                               text='🟡 Этот бот уже был добавлен.')
                    Thread(target=delete_messages, args=(3, message.chat.id, message.message_id, x.message_id)).start()
            else:
                x = await bot.send_message(chat_id=message.chat.id,
                                           text='🛑 Токен бота или некорректен или бот уже подключен к другому обработчику! Пожалуйста, или введите корректный токен или отключите бота от другого обработчика.\n\n_Вы всегда можете проверить правильность токена бота в @BotFather_',
                                           parse_mode='markdown')
                Thread(target=delete_messages, args=(4, message.chat.id, message.message_id, x.message_id)).start()

    async def advertisement_cabinet_starter(message: types.Message):
        Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
        back_to_main_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_to_main_menu_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
        await bot.send_message(message.chat.id, text='🟢', reply_markup=back_to_main_menu_markup)
        await UserState.advertisement_cabinet.set()
        await advertisement_cabinet(message)

    async def advertisement_cabinet(message):
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        markup = types.InlineKeyboardMarkup()
        for button_data in [['➕ Создать объявление', 'create_ads'],
                            ['📥 Управление объявлениями', 'manage_advertisements']]:
            markup.add(types.InlineKeyboardButton(text=button_data[0], callback_data=button_data[1]))
        markup.add(types.InlineKeyboardButton(text='❓ Вопросы и ответы',
                                              url='https://telegra.ph/Kak-rabotaet-reklama-v-ReshenijaBot-i-botah-dvizhka-ReshenijaBot-08-25'))
        advertisements_cabinet_message_text = f'🏟 Рекламный кабинет\n\nℹ️ Здесь вы можете купить показы рекламы вашего канала, бота, сайта и тп в сообщениях ботов движка @ReshenijaBot. "Сообщения ботов движка @ReshenijaBot" - это сам @ReshenijaBot, и все остальные боты, созданныен при помощи его движка. На данный момент в общей сложности в @ReshenijaBot и других ботах его движка *{await get_amount_of_users_in_all_bots()}* пользователей.\n\n👥 Аудитория - *активные* пользователи telegram, подростки, школьники, студенты из стран СНГ.'
        if isinstance(message, types.Message):
            chat_id = message.chat.id
        else:
            chat_id = message.message.chat.id
        if 'id_of_message_with_markup' in dictionary_used_in_this_function:
            id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
        else:
            id_of_message = None
        message_id = await try_edit_or_send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                    chat_id=chat_id, text=advertisements_cabinet_message_text,
                                                    message_id=id_of_message, reply_markup=markup,
                                                    parse_mode='markdown')
        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    @dp.callback_query_handler(lambda call: True, state=UserState.advertisement_cabinet)
    async def advertisement_cabinet_buttons_handler(call: types.CallbackQuery, state: FSMContext):
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        if await check_ads_message_buttons_call(call):
            return
        if call.data == 'create_ads':
            await UserState.advertisement_watching.set()
            await buy_advertisements(call)
        elif call.data == 'manage_advertisements':
            await UserState.manage_advertisements.set()
            await view_orders(call)

    async def view_orders(call: types.CallbackQuery):
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
        if 'ads_ids' in users_data and users_data['ads_ids']:
            ads_ids = users_data['ads_ids']
            markup = types.InlineKeyboardMarkup()
            for ads_id in ads_ids:
                try:
                    ads_info = await get_ads_data(ads_id)
                    markup.add(types.InlineKeyboardButton(
                        text=f"№{ads_id} ({ads_info['text'][:6] + '...'}) - {ads_info['watches_ordered']}",
                        callback_data=ads_id))
                except Exception:
                    pass
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_advertisement_cabinet'))
            view_orders_message_text = '📥 Выберите рекламное объявление из списка ниже!'
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id, text=view_orders_message_text,
                                                        message_id=id_of_message,
                                                        reply_markup=markup)
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_advertisement_cabinet'))
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id,
                                                        text='Пока вы не создали ни одного рекламного объявления',
                                                        message_id=id_of_message,
                                                        reply_markup=markup)
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    async def view_ads_info(call: types.CallbackQuery, is_admin=False,
                            previous_call_data='back_to_manage_advertisements'):
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        ads_info = await get_ads_data(call.data)
        markup = types.InlineKeyboardMarkup()
        if ads_info['status'] == 3 and not is_admin:
            markup.add(types.InlineKeyboardButton(text='💳 Оплатить', callback_data=f'pay_{call.data}'))
        if ads_info['status'] == 1 and is_admin:
            markup.add(*[types.InlineKeyboardButton(text='✅', callback_data=f'pass_moderation_{call.data}'),
                         types.InlineKeyboardButton(text='❌', callback_data=f'reject_moderation_{call.data}')])
        markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data=previous_call_data))
        ads_info_message_text = f"💠 Объявление *№{call.data}*\n\nТекст: {ads_info['text']}\n\nЗаказано просмотров: *{ads_info['watches_ordered']}*\nЦена: *{ads_info['price']}*\n\nСтатистика:\n👀 Показов - *{ads_info['amount_of_watches']}*\n\nСтатус: {await ads_status_to_text(ads_info['status'])}"
        if 'id_of_message_with_markup' in dictionary_used_in_this_function:
            id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
        else:
            id_of_message = None
        message_id = await send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id, chat_id=call.message.chat.id,
                                        text=ads_info_message_text,
                                        message_id=id_of_message,
                                        reply_markup=markup, parse_mode='markdown')
        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    async def process_payments():
        global on_processing_advertisements_payments
        while True:
            all_payments_data = get_all_payments_data()
            for payment_data in all_payments_data:
                if payment_data[-1] == 1:
                    is_paid = await check_payment(f'{payment_data[1]}_{payment_data[0]}')
                else:
                    is_paid = await check_payment(payment_data[0])
                if is_paid:
                    if payment_data[-1] == 1:
                        await change_ads_status(payment_data[0], 4, {'bot_token': payment_data[3],
                                                                     'chat_id': payment_data[2]})
                        await delete_payment(payment_data[0])
                    else:
                        await set_pro_for_user(payment_data[1], int(payment_data[0].split('_')[1]), payment_data[2],
                                               payment_data[3])
                        await delete_payment(payment_data[0], 2)
                else:
                    if payment_data[4] == 899:
                        await delete_payment(payment_data[0], payment_data[-1])
                    else:
                        await increase_processing_time(payment_data[0], payment_data[-1])
            time.sleep(1)
            if len(all_payments_data) == 0:
                on_processing_advertisements_payments = False
                return

    async def pay_ads(call: types.CallbackQuery):
        global on_processing_advertisements_payments
        await UserState.ads_buying.set()
        ads_id = call.data.split('_')[1]
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
        await add_payment(ads_id, call.from_user.id, call.message.chat.id, token)
        if not on_processing_advertisements_payments:
            on_processing_advertisements_payments = True
            Thread(target=async_functions_process_starter, args=(process_payments, [])).start()
        ads_info = await get_ads_data(ads_id)
        if str(call.from_user.id) in ADMINS:
            ads_info['price'] = 2
        payment_link = await get_payment_link(f'{call.from_user.id}_{ads_id}', ads_info['price'], 1)
        markup = types.InlineKeyboardMarkup()
        markup.add(*[types.InlineKeyboardButton(text=f"💳 Оплатить ({ads_info['price']}₽)", url=payment_link),
                     types.InlineKeyboardButton(text='🔄 Проверить',
                                                callback_data=f'check-{call.from_user.id}_{ads_id}')])
        markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data=f'ads_{ads_id}'))
        pay_ads_message_text = f'Вы собираетесь оплатить объявление *№{call.data.split("_")[-1]}*\n\nТекст: {ads_info["text"]}\n\nЗаказано просмотров: *{ads_info["watches_ordered"]}*\nЦена: *{ads_info["price"]}*.\n\n❕ Если в течении минуты после оплаты бот не отправит вам сообщение о том, что заказ оплачен, и показ рекламы запущен, нажмите на кнопку *"🔄 Проверить"*. Если это не помогло, напишите нам в [поддержку](https://t.me/ReshenijaSupportBot).'
        if 'id_of_message_with_markup' in dictionary_used_in_this_function:
            id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
        else:
            id_of_message = None
        message_id = await send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id, chat_id=call.message.chat.id,
                                        text=pay_ads_message_text,
                                        message_id=id_of_message,
                                        reply_markup=markup, parse_mode='markdown')
        users_data['id_of_ads_paid_message'] = message_id
        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(users_data), 1])).start()
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    @dp.callback_query_handler(lambda call: True, state=UserState.ads_buying)
    async def ads_buying_buttons_handler(call: types.CallbackQuery, state: FSMContext):
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        if await check_ads_message_buttons_call(call):
            return
        if 'check' in call.data:
            await check_payment_by_button(call, 1)

    @dp.callback_query_handler(lambda call: True, state=UserState.manage_advertisements)
    async def view_orders_buttons_handler(call: types.CallbackQuery, state: FSMContext):
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        if await check_ads_message_buttons_call(call):
            return
        users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
        if call.data == 'back_to_advertisement_cabinet':
            await UserState.advertisement_cabinet.set()
            await advertisement_cabinet(call)
        elif call.data == 'back_to_manage_advertisements':
            await view_orders(call)
        elif 'ads_ids' in users_data and int(call.data) in users_data['ads_ids']:
            await view_ads_info(call)

    async def buy_advertisements(call: types.CallbackQuery, on_edit=False):
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        dictionary_used_in_this_function['own-quantity'] = False
        markup = types.InlineKeyboardMarkup()
        for amount_ads in PRICES_FOR_ADS:
            price_button_text = f'{amount_ads} • {PRICES_FOR_ADS[amount_ads]}₽'
            if amount_ads > 1000:
                price_button_text += f'  🤑 Скидка: {int(((amount_ads * PRICE_FOR_WATCH - PRICES_FOR_ADS[amount_ads]) / (amount_ads * PRICE_FOR_WATCH)) * 100)}%'
            if on_edit:
                markup.add(
                    types.InlineKeyboardButton(text=price_button_text,
                                               callback_data=f'ads-{amount_ads}-{PRICES_FOR_ADS[amount_ads]}_True'))
            else:
                markup.add(types.InlineKeyboardButton(text=price_button_text,
                                                      callback_data=f'ads-{amount_ads}-{PRICES_FOR_ADS[amount_ads]}'))
        if on_edit:
            markup.add(types.InlineKeyboardButton(text='♾ Свое количество', callback_data='own-quantity_True'))
        else:
            markup.add(types.InlineKeyboardButton(text='♾ Свое количество', callback_data='own-quantity'))
        markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_advertisement_cabinet'))
        if 'id_of_message_with_markup' in dictionary_used_in_this_function:
            id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
        else:
            id_of_message = None
        message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                    chat_id=call.message.chat.id,
                                                    text='💬 Выбери необходимое количество просмотров рекламного сообщения',
                                                    message_id=id_of_message, reply_markup=markup)
        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    @dp.callback_query_handler(lambda call: True,
                               state=[UserState.advertisement_watching, UserState.on_ads_text_getting])
    async def buy_advertisement_buttons_handler(call: types.CallbackQuery, state: FSMContext):
        if await check_ads_message_buttons_call(call):
            return
        elif 'own-quantity' in call.data:
            Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
            dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
            dictionary_used_in_this_function['own-quantity'] = True
            markup = types.InlineKeyboardMarkup()
            for button_text in [['- 100', '+ 100'], ['- 1000', '+ 1000'], ['- 10000', '+ 10000']]:
                if 'True' in call.data:
                    markup.add(
                        *[types.InlineKeyboardButton(text=button_text[0], callback_data=f'{button_text[0]}_True'),
                          types.InlineKeyboardButton(text=button_text[1], callback_data=f'{button_text[1]}_True')])
                else:
                    markup.add(*[types.InlineKeyboardButton(text=button_text[0], callback_data=button_text[0]),
                                 types.InlineKeyboardButton(text=button_text[1], callback_data=button_text[1])])
            markup.add(types.InlineKeyboardButton(text='✅ Продолжить', callback_data='continue'))
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_buy_advertisements'))
            quantity_of_watches = 500
            dictionary_used_in_this_function['quantity_of_watches'] = quantity_of_watches
            if quantity_of_watches >= 100000:
                price = (PRICES_FOR_ADS[100000] / 100000) * quantity_of_watches
            elif quantity_of_watches >= 10000:
                price = (PRICES_FOR_ADS[10000] / 10000) * quantity_of_watches
            else:
                price = quantity_of_watches * PRICE_FOR_WATCH
            dictionary_used_in_this_function['price'] = price
            own_quantity_message_text = f'⏺ Количество показов вашей рекламы - *{quantity_of_watches}*\n\n💳 Итоговая сумма: *{price if ".0" not in str(price) else int(price)} ₽*\n\n❌ Минимальное количество показов - *500*\n❎ Максимальное количество показов - *200000*'
            await answer_callback_query(call, bot)
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id, text=own_quantity_message_text,
                                                        message_id=call.message.message_id, reply_markup=markup,
                                                        parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif call.data == 'back_to_buy_advertisements':
            await UserState.advertisement_watching.set()
            await buy_advertisements(call)
        elif call.data == 'back_to_advertisement_cabinet':
            await UserState.advertisement_cabinet.set()
            await advertisement_cabinet(call)
        elif call.data == 'edit_price':
            dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
            if 'id_of_wrong_ads_texts_messages' in dictionary_used_in_this_function and \
                    dictionary_used_in_this_function['id_of_wrong_ads_texts_messages']:
                Thread(target=delete_messages,
                       args=(0, *dictionary_used_in_this_function['id_of_wrong_ads_texts_messages'])).start()
            await buy_advertisements(call, True)
        elif ('+' in call.data or '-' in call.data) and call.data.split('_')[0][2:].isdigit():
            Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
            markup = types.InlineKeyboardMarkup()
            for button_text in [['- 100', '+ 100'], ['- 1000', '+ 1000'], ['- 10000', '+ 10000']]:
                if 'True' in call.data:
                    markup.add(
                        *[types.InlineKeyboardButton(text=button_text[0], callback_data=f'{button_text[0]}_True'),
                          types.InlineKeyboardButton(text=button_text[1], callback_data=f'{button_text[1]}_True')])
                else:
                    markup.add(*[types.InlineKeyboardButton(text=button_text[0], callback_data=button_text[0]),
                                 types.InlineKeyboardButton(text=button_text[1], callback_data=button_text[1])])
            if 'True' in call.data:
                markup.add(types.InlineKeyboardButton(text='✅ Продолжить', callback_data='continue_True'))
            else:
                markup.add(types.InlineKeyboardButton(text='✅ Продолжить', callback_data='continue'))
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_buy_advertisements'))
            dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
            try:
                quantity_of_watches = dictionary_used_in_this_function['quantity_of_watches']
            except KeyError:
                quantity_of_watches = 500
            quantity_of_watches = eval(f"{quantity_of_watches} {call.data.split('_')[0]}")
            if quantity_of_watches < 500:
                quantity_of_watches = 500
            if quantity_of_watches > 200000:
                quantity_of_watches = 200000
            dictionary_used_in_this_function['quantity_of_watches'] = quantity_of_watches
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            if quantity_of_watches >= 100000:
                price = (PRICES_FOR_ADS[100000] / 100000) * quantity_of_watches
            elif quantity_of_watches >= 10000:
                price = (PRICES_FOR_ADS[10000] / 10000) * quantity_of_watches
            else:
                price = quantity_of_watches * PRICE_FOR_WATCH
            dictionary_used_in_this_function['price'] = price
            own_quantity_message_text = f'⏺ Количество показов вашей рекламы - *{quantity_of_watches}*\n\n💳 Итоговая сумма: *{price if ".0" not in str(price) else int(price)} ₽*\n\n❌ Минимальное количество показов - *500*\n❎ Максимальное количество показов - *200000*'
            await answer_callback_query(call, bot)
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id, text=own_quantity_message_text,
                                                        message_id=call.message.message_id, reply_markup=markup,
                                                        parse_mode='markdown')
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif 'continue' in call.data or 'ads' in call.data:
            await UserState.advertisement_watching.set()
            Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_id])).start()
            dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
            if 'id_of_wrong_ads_texts_messages' in dictionary_used_in_this_function and \
                    dictionary_used_in_this_function['id_of_wrong_ads_texts_messages']:
                Thread(target=delete_messages,
                       args=(0, *dictionary_used_in_this_function['id_of_wrong_ads_texts_messages'])).start()
            if 'ads' in call.data:
                dictionary_used_in_this_function['quantity_of_watches'] = int(call.data.split('-')[1])
                dictionary_used_in_this_function['price'] = int(call.data.split('-')[2].split('_')[0])
            if 'True' in call.data:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(text='✍️ Изменить текст', callback_data='continue_edit'))
                markup.add(
                    types.InlineKeyboardButton(text='👀 Изменить количество просмотров', callback_data='edit_price'))
                markup.add(types.InlineKeyboardButton(text='✅ Продолжить', callback_data='send_to_moderation'))
                message_text = dictionary_used_in_this_function['ads_message_text'].replace('*', '\*').replace('_',
                                                                                                               '\_')
                message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                            chat_id=call.message.chat.id,
                                                            text=f"Состав вашего заказа:\n\n👀 Количество просмотров: *{dictionary_used_in_this_function['quantity_of_watches']}*\n💳 Цена: *{dictionary_used_in_this_function['price']} ₽*\n📝 Текст: {message_text}",
                                                            message_id=call.message.message_id, reply_markup=markup,
                                                            parse_mode='markdownv2')
                dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            else:
                markup = types.InlineKeyboardMarkup()
                if 'own-quantity' in dictionary_used_in_this_function and \
                        dictionary_used_in_this_function['own-quantity']:
                    callback_data = '+ 0'
                else:
                    if 'edit' in call.data:
                        callback_data = 'continue_True'
                    else:
                        callback_data = 'back_to_buy_advertisements'
                markup.add(types.InlineKeyboardButton(text='❌ Отмена', callback_data=callback_data))
                enter_your_ads_text = '⬇️ Отправьте в этот чат текст вашего рекламного сообщения *в одну строку*.\n\nℹ️ В тексте сообщения допускается использования *одного* @username или *одной* ссылки. Соблюдайте пунктуацию и орфографию. Максимальная длина сообщения - *170* символов. Минимальная длина сообщения - *20* символов. Допускается использование букв русского и английского алфавита, цифр, а также некоторых спецсимволов. Смайлы *запрещены*.'
                if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                    id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
                else:
                    id_of_message = None
                message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                            chat_id=call.message.chat.id, text=enter_your_ads_text,
                                                            message_id=id_of_message, reply_markup=markup,
                                                            parse_mode='markdown')
                dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                dictionary_used_in_this_function['on_ads_text_getting'] = True
                await UserState.on_ads_text_getting.set()
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif call.data == 'send_to_moderation':
            dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
            if 'id_of_wrong_ads_texts_messages' in dictionary_used_in_this_function and \
                    dictionary_used_in_this_function['id_of_wrong_ads_texts_messages']:
                Thread(target=delete_messages,
                       args=(0, *dictionary_used_in_this_function['id_of_wrong_ads_texts_messages'])).start()
            users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)

            id_of_ads = await create_ads(call.from_user.id, call.message.chat.id, token,
                                         dictionary_used_in_this_function['quantity_of_watches'],
                                         dictionary_used_in_this_function['price'],
                                         dictionary_used_in_this_function['ads_message_text'])
            if 'ads_ids' not in users_data:
                users_data['ads_ids'] = [id_of_ads]
            else:
                if id_of_ads not in users_data['ads_ids']:
                    users_data['ads_ids'].append(id_of_ads)
            try:
                await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception:
                pass
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(text='⏪ В рекламный кабинет', callback_data='back_to_advertisement_cabinet'))
            if str(call.from_user.id) in ADMINS:
                send_to_moderation_text = 'ℹ️ Админ, показ вашего рекламного сообщения запущен!'
            else:
                send_to_moderation_text = 'ℹ️ Ваше рекламное сообщение отправлено на модерацию. После ее прохождения вы сможете совершить оплату.'
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id, text=send_to_moderation_text,
                                                        message_id=id_of_message,
                                                        reply_markup=markup)
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(users_data), 1])).start()

    @dp.message_handler(state=UserState.on_ads_text_getting, content_types=['text'])
    async def get_ads_text(message: types.Message, state: FSMContext):
        if message.text == '↩ Назад в главное меню' or message.text in MAIN_COMMANDS:
            await command_handler(message, state)
        else:
            dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
            if 'id_of_wrong_ads_texts_messages' in dictionary_used_in_this_function and \
                    dictionary_used_in_this_function['id_of_wrong_ads_texts_messages']:
                Thread(target=delete_messages,
                       args=(0, *dictionary_used_in_this_function['id_of_wrong_ads_texts_messages'])).start()
            if len(message.text) > 170:
                x = await bot.send_message(chat_id=message.chat.id,
                                           text='🛑 Рекламное сообщение слишком длинное! Максимальная длина - 170 символов.')
                dictionary_used_in_this_function['id_of_wrong_ads_texts_messages'] = [message.chat.id,
                                                                                      message.message_id, x.message_id]
            elif len(message.text) < 20:
                x = await bot.send_message(chat_id=message.chat.id,
                                           text='🛑 Рекламное сообщение слишком короткое! Минимальная длина - 20 символов.')
                dictionary_used_in_this_function['id_of_wrong_ads_texts_messages'] = [message.chat.id,
                                                                                      message.message_id,
                                                                                      x.message_id]
            elif not contains_only_allowed_chars(message.text):
                x = await bot.send_message(chat_id=message.chat.id,
                                           text='🛑 Текст рекламного сообщения содержит недопустимые символы!')
                dictionary_used_in_this_function['id_of_wrong_ads_texts_messages'] = [message.chat.id,
                                                                                      message.message_id,
                                                                                      x.message_id]
            else:
                dictionary_used_in_this_function['ads_message_text'] = message.text
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(text='✍️ Изменить текст', callback_data='continue_edit'))
                markup.add(
                    types.InlineKeyboardButton(text='👀 Изменить количество просмотров', callback_data='edit_price'))
                markup.add(types.InlineKeyboardButton(text='✅ Продолжить', callback_data='send_to_moderation'))
                message_text = message.text.replace('*', '\*').replace('_', '\_')
                await UserState.advertisement_watching.set()
                message_id = await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                chat_id=message.chat.id,
                                                text=f"Состав вашего заказа:\n\n👀 Количество просмотров: *{dictionary_used_in_this_function['quantity_of_watches']}*\n💳 Цена: *{dictionary_used_in_this_function['price']} ₽*\n📝 Текст: {message_text}",
                                                reply_markup=markup, parse_mode='markdown')
                dictionary_used_in_this_function['id_of_wrong_ads_texts_messages'] = [message.chat.id,
                                                                                      message.message_id,
                                                                                      message_id]
                dictionary_used_in_this_function['on_ads_text_getting'] = False
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    async def pass_or_reject_moderation(call: types.CallbackQuery, update_ads_info_message=False):
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        ads_id = int(call.data.split('_')[2])
        if 'pass' in call.data:
            try:
                await change_ads_status(ads_id, 3)
                answer_text = f'Объявление №{ads_id} прошло модерацию'
            except Exception:
                answer_text = 'Статус объявления не может быть изменен'
            try:
                await answer_callback_query(call, bot, answer_text)
            except Exception:
                pass
        elif 'reject' in call.data:
            try:
                await change_ads_status(ads_id, 2)
                answer_text = f'Объявление №{ads_id} не прошло модерацию'
            except Exception:
                answer_text = 'Статус объявления не может быть изменен'
            try:
                await answer_callback_query(call, bot, answer_text)
            except Exception:
                pass
        if update_ads_info_message:
            if 'previous_call_data' in dictionary_used_in_this_function:
                previous_call_data = dictionary_used_in_this_function['previous_call_data']
            else:
                previous_call_data = 'id'
            call.data = ads_id
            await view_ads_info(call, True, previous_call_data)
        else:
            try:
                await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception:
                pass

    async def for_developers(message):
        Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
        back_to_main_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_to_main_menu_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
        if isinstance(message, types.Message):
            chat_id = message.chat.id
            await bot.send_message(chat_id, text='🟢', reply_markup=back_to_main_menu_markup)
        else:
            chat_id = message.message.chat.id
        dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        markup = types.InlineKeyboardMarkup()
        for button_data in [['🏟 Рекламные заказы', 'ads_orders']]:
            markup.add(types.InlineKeyboardButton(text=button_data[0], callback_data=button_data[1]))
        for_developers_message_text = 'Выбери необходимый пункт!'
        await UserState.for_developers.set()
        if 'id_of_message_with_markup' in dictionary_used_in_this_function:
            id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
        else:
            id_of_message = None
        message_id = await try_edit_or_send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id,
                                                    chat_id=chat_id, text=for_developers_message_text,
                                                    message_id=id_of_message,
                                                    reply_markup=markup)
        dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    @dp.callback_query_handler(lambda call: True, state=UserState.for_developers)
    async def for_developers_buttons_handler(call: types.CallbackQuery, state: FSMContext):
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        if call.data == 'ads_orders':
            markup = types.InlineKeyboardMarkup()
            for button_data in [['🛡 Ожидают модерации', 'id_1'], ['❌ Не прошли модерацию', 'id_2'],
                                ['💳 Ожидают оплаты', 'id_3'], ['⏳ Выполняются', 'id_4'], ['✅ Выполнены', 'id_5'],
                                ['💠 Все', 'id_None']]:
                markup.add(types.InlineKeyboardButton(text=button_data[0], callback_data=button_data[1]))
            markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='back_to_for_developers'))
            view_types_of_orders_message_text = '⬇️ Выбери статус заказа'
            if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
            else:
                id_of_message = None
            message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                        chat_id=call.message.chat.id,
                                                        text=view_types_of_orders_message_text,
                                                        message_id=id_of_message,
                                                        reply_markup=markup)
            dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif call.data == 'back_to_for_developers':
            await for_developers(call)
        elif 'id' in call.data:
            status_code = eval(call.data[3:])
            dictionary_used_in_this_function['previous_call_data'] = call.data
            ads_orders_data = await get_ads_orders_by_status_code(status_code)
            markup = types.InlineKeyboardMarkup()
            if ads_orders_data:
                for ads_id in ads_orders_data:
                    ads_info = ads_orders_data[ads_id]
                    markup.add(types.InlineKeyboardButton(
                        text=f"№{ads_id} ({ads_info['text'][:6] + '...'}) - {ads_info['watches_ordered']}",
                        callback_data=f'ads_{ads_id}'))
                markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='ads_orders'))
                view_orders_message_text = f'⬇️ Выбери необходимое рекламное объявление из списка ниже!\n\nРаздел: *"{await status_code_to_menu_text(status_code)}"*\n\nКоличество рекламных объявлений: *{len(ads_orders_data)}*'
                if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                    id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
                else:
                    id_of_message = None
                message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                            chat_id=call.message.chat.id, text=view_orders_message_text,
                                                            message_id=id_of_message, reply_markup=markup,
                                                            parse_mode='markdown')
                dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(text='⏪ Назад', callback_data='ads_orders'))
                if 'id_of_message_with_markup' in dictionary_used_in_this_function:
                    id_of_message = dictionary_used_in_this_function['id_of_message_with_markup']
                else:
                    id_of_message = None
                message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot, bot_id=bot_id,
                                                            chat_id=call.message.chat.id,
                                                            text=f'Пока в разделе *"{await status_code_to_menu_text(status_code)}"* нет ни одного рекламного объявления!',
                                                            message_id=id_of_message, reply_markup=markup,
                                                            parse_mode='markdown')
                dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()
        elif 'ads_' in call.data:
            call.data = call.data[4:]
            if 'previous_call_data' in dictionary_used_in_this_function:
                previous_call_data = dictionary_used_in_this_function['previous_call_data']
            else:
                previous_call_data = 'id'
            await view_ads_info(call, True, previous_call_data)
        elif 'pass_moderation_' in call.data or 'reject_moderation_' in call.data:
            await pass_or_reject_moderation(call, True)

    @dp.callback_query_handler(lambda call: True, state='*')
    async def all_buttons_handler(call: types.CallbackQuery, state: FSMContext = None):
        if await check_ads_message_buttons_call(call):
            return
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_id, 2)
        users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
        dictionary_used_in_this_function['text_inputed'] = False
        dictionary_used_in_this_function['bookmark_dict'] = {}
        dictionary_used_in_this_function['id_of_message_with_markup'] = call.message.message_id
        flag = False
        for key in list(dictionary_used_in_this_function.keys()):
            if isinstance(dictionary_used_in_this_function[key], list) or isinstance(
                    dictionary_used_in_this_function[key],
                    dict):
                if call.data in dictionary_used_in_this_function[key] or 'двз' in call.data or 'share' in call.data or \
                        call.data in ['⁉️ Найти решение', 'bookmarks', 'А почему не отправляются ?']:
                    flag = True
                    await UserState.find_solution.set()
                    await gdz_main_function(call, dictionary_used_in_this_function, state)
                    break
        if not flag:
            # проверить есть ли call.data в списке всех закладок
            users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
            try:
                bookmarks = users_data['bookmarks']
            except KeyError:
                bookmarks = {}
            for key in bookmarks:
                if call.data == key:
                    flag = True
                    await UserState.bookmark_working.set()
                    await get_bookmark(call, state)
                    break
        if not flag:
            if call.data in ['back_to_bookmarks', 'bookmarks']:
                flag = True
                await get_bookmarks(call)
        if not flag:
            if call.data in ['open_bookmark', 'delete_bookmark']:
                users_data = await get_dictionary(str(call.from_user.id), bot_id, 1)
                await UserState.bookmark_opening.set()
                try:
                    res = users_data['bookmarks']
                except KeyError:
                    res = {}
                bookmark = res[dictionary_used_in_this_function['current_bookmark']]
                await state.update_data(bookmark_dict=bookmark,
                                        bookmark_name=dictionary_used_in_this_function['current_bookmark'])
                await bookmark_opening(call, state)
        if not flag:
            try:
                users_bots = users_data['bots']
            except KeyError:
                users_bots = {}
            if call.data in ['my_referrals', 'my_bots', 'add_bot', 'buy_pro'] or call.data in users_bots or \
                    'start' in call.data or 'stop' in call.data or 'delete' in call.data or 'confirm_deletion' in \
                    call.data:
                await UserState.my_account.set()
                await my_account_buttons_handler(call, state)
            elif call.data == 'back_to_my_account':
                await UserState.my_account.set()
                await my_account_starter(call)
        if not flag:
            if call.data in ['create_ads', 'manage_advertisements', 'questions_and_answers']:
                await UserState.advertisement_cabinet.set()
                await advertisement_cabinet_buttons_handler(call, state)
            elif ('ads_ids' in users_data and call.data.isdigit() and int(call.data) in users_data['ads_ids']) or \
                    call.data in ['back_to_advertisement_cabinet', 'back_to_manage_advertisements'] or \
                    'previous_call_data' in dictionary_used_in_this_function and call.data == \
                    dictionary_used_in_this_function['previous_call_data']:
                await UserState.manage_advertisements.set()
                await view_orders_buttons_handler(call, state)
            elif 'check' in call.data:
                if call.data[6:].split('_')[-1].isdigit():
                    await ads_buying_buttons_handler(call, state)
                else:
                    await check_payment_by_button(call, 2)
            elif 'own-quantity' in call.data or call.data in \
                    ['back_to_buy_advertisements', 'back_to_advertisement_cabinet', 'edit_price', 'send_to_moderation'] \
                    or ('+' in call.data or '-' in call.data) and call.data.split('_')[0][2:].isdigit() or 'continue' \
                    in call.data or 'ads' in call.data:
                await UserState.advertisement_watching.set()
                await buy_advertisement_buttons_handler(call, state)
            elif 'pro_' in call.data:
                await UserState.on_pro.set()
                await buy_pro_buttons_handler(call, state)
            elif 'gpt-' in call.data or call.data == 'back_to_model_selection':
                await get_chat_gpt_version(call, state)
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_id, str(dictionary_used_in_this_function), 2])).start()

    @dp.message_handler(state='*', commands=['statistics'])
    async def statistics(message: types.message):
        await UserState.find_solution.set()
        await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id, chat_id=message.chat.id,
                           text=await check_amount_of_users(message, bot_id),
                           reply_markup=await get_reply_markup_for_user(message.from_user.id))

    @dp.message_handler(state='*', commands=['my_account'])
    async def my_account(message: types.Message):
        Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
        back_to_main_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_to_main_menu_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
        await bot.send_message(message.chat.id, text='🟢', reply_markup=back_to_main_menu_markup)
        await my_account_starter(message)
        await UserState.my_account.set()

    @dp.message_handler(state='*', commands=['gift'])
    async def gift_pro_starter(message: types.Message):
        user_data = message.get_args()
        try:
            user_id, months = list(map(int, user_data.split(' ')))
            await gift_pro(message, user_id, months)
        except Exception:
            if str(message.from_user.id) not in ADMINS:
                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            else:
                await UserState.on_gifting_pro.set()
                await bot.send_message(chat_id=message.chat.id,
                                       text='⭐️ Пришли данные того, кому хочешь подарить PRO подписку. В формате "id количество месяцев"')

    @dp.message_handler(state=UserState.on_gifting_pro)
    async def gift_pro(message: types.Message, user_id=None, months=None):
        try:
            if not user_id or not months:
                user_id, months = list(map(int, message.text.split()[:2]))
            if await is_pro(user_id):
                raise Exception
            await set_pro_for_user(user_id, months, None, None)
            await bot.send_message(chat_id=message.chat.id, text=f'💎 Вы подарили PRO подписку пользователю {user_id}')
            await UserState.previous()
        except Exception as e:
            await bot.send_message(chat_id=message.chat.id,
                                   text=f'❌ Не удалось подарить подписку. Попробуй еще раз! Возникла ошибка "{e}".')

    @dp.message_handler(state='*', commands=['unsubscribe'])
    async def unsubscribe_from_pro_starter(message: types.Message):
        try:
            user_id = int(message.get_args())
            await unsubscribe_from_pro(message, user_id)
        except Exception:
            if str(message.from_user.id) not in ADMINS:
                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            else:
                await UserState.on_unsubscribing_pro.set()
                await bot.send_message(chat_id=message.chat.id,
                                       text='🚫 Пришли id того, у кого хочешь отобрать подписку.')

    @dp.message_handler(state=UserState.on_unsubscribing_pro)
    async def unsubscribe_from_pro(message: types.Message, user_id: int = None):
        try:
            if user_id is None:
                user_id = int(message.text)
            if not await is_pro(message.from_user.id) and message.text in ADMINS:
                raise Exception
            time_left = await get_the_rest_of_the_subscription_days(user_id)
            days_left = 365 * time_left[0] + 30 * time_left[1] + time_left[2]
            conn = sqlite3.connect('./data/databases/pro_users.sqlite3')
            c = conn.cursor()
            c.execute(
                'CREATE TABLE IF NOT EXISTS pro_users_data (id INTEGER, creation_date TEXT, months INTEGER, expired_date TEXT, chat_id INTEGER, bot_token TEXT)')
            months = c.execute(f'SELECT months  FROM pro_users_data WHERE id=?', (user_id,)).fetchone()[0]
            c.execute(f'DELETE FROM pro_users_data WHERE id=?', (user_id,))
            conn.commit()
            c.close()
            conn.close()
            if months in {1: 100, 3: 250, 6: 500}:
                price_for_one_day = {1: 100, 3: 250, 6: 500}[months] / (months * 30)
            else:
                price_for_one_day = (months * 100) / (months * 30)
            await bot.send_message(chat_id=message.chat.id,
                                   text=f'⭕️ Вы отменили PRO подписку пользователю {user_id}. Предполагаемая сумма для возврата - {round(days_left * price_for_one_day)}₽.')
            await UserState.previous()
        except Exception as e:
            await bot.send_message(chat_id=message.chat.id,
                                   text=f'❌ Не удалось отменить подписку. Попробуй еще раз! Возникла ошибка "{e}".')

    # handler отвечающий за обработку все текстовых сообщений и нажатие ReplyKeyboardButton
    @dp.message_handler(state=[UserState.find_solution, UserState.chat_gpt_writer, UserState.bookmark_working,
                               UserState.bookmark_opening, UserState.bookmark_creation, None],
                        content_types=['text', 'voice', 'photo'])
    async def command_handler(message: types.Message, state: FSMContext):
        await state.reset_state(with_data=True)
        dictionary_to_use_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
        if 'text_inputed' in dictionary_to_use_in_this_function and 'bookmark_dict' in \
                dictionary_to_use_in_this_function and message.text not in await \
                get_buttons_list_for_user(message.from_user.id) + ['↩ Назад в главное меню'] + MAIN_COMMANDS:
            if dictionary_to_use_in_this_function['text_inputed'] and \
                    dictionary_to_use_in_this_function['bookmark_dict']:
                await UserState.bookmark_creation.set()
                await state.update_data(bookmark_dict=dictionary_to_use_in_this_function['bookmark_dict'])
                await get_name_of_bookmark(message, state)
        elif 'text_get_for_chat_gpt' in dictionary_to_use_in_this_function and message.text not in await \
                get_buttons_list_for_user(message.from_user.id) + ['↩ Назад в главное меню',
                                                                   '🗑 Очистить историю диалога'] + MAIN_COMMANDS:
            if dictionary_to_use_in_this_function['text_get_for_chat_gpt']:
                await UserState.chat_gpt_writer.set()
                await chat_gpt_task_handler(message)
            else:
                try:
                    await message.delete()
                except Exception:
                    pass
        elif 'text_get_for_chat_gpt' in dictionary_to_use_in_this_function and message.text not in await \
                get_buttons_list_for_user(message.from_user.id) + ['↩ Назад в главное меню'] + MAIN_COMMANDS \
                and message.text == '🗑 Очистить историю диалога':
            await clear_chat_gpt_conversation(message)
        elif 'on_new_bot_creation' in dictionary_to_use_in_this_function and message.text not in await \
                get_buttons_list_for_user(message.from_user.id) + ['↩ Назад в главное меню'] + MAIN_COMMANDS:
            if dictionary_to_use_in_this_function['on_new_bot_creation']:
                await UserState.new_bot_creation.set()
                await new_bot_token_getting_handler(message, state)
        elif 'on_ads_text_getting' in dictionary_to_use_in_this_function and message.text not in await \
                get_buttons_list_for_user(message.from_user.id) + ['↩ Назад в главное меню'] + MAIN_COMMANDS:
            if dictionary_to_use_in_this_function['on_ads_text_getting']:
                await UserState.on_ads_text_getting.set()
                await get_ads_text(message, state)
        elif dictionary_to_use_in_this_function:
            dictionary_to_use_in_this_function['chat_gpt_mode'] = 0
            Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id, bot_id])).start()
            try:
                dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_id, 2)
                try:
                    await bot.delete_message(chat_id=message.chat.id,
                                             message_id=dictionary_used_in_this_function['id_of_message_with_markup'])
                except Exception:
                    pass
            except Exception:
                pass
            if message.text == '📈 Статистика' or message.text == '/statistics':
                await statistics(message)
            elif message.text == '⁉️ Найти решение':
                await find_solution(message)
            elif message.text == '🤖 ИИ Chat GPT' or message.text == '/chat_gpt':
                await chat_gpt_starter(message)
            elif message.text == '📌 Закладки' or message.text == '/bookmarks':
                await get_bookmarks(message)
            elif message.text == '👤 Мой аккаунт' or message.text == '/my_account':
                await my_account(message)
            elif message.text == 'ℹ️ Информация о боте':
                await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id, chat_id=message.chat.id,
                                   text=await bot_information(message, bot_id),
                                   reply_markup=await get_reply_markup_for_user(message.from_user.id),
                                   parse_mode='markdown')
            elif message.text == '🏟 Реклама':
                await advertisement_cabinet_starter(message)
            elif message.text == '💻 Для разработчиков' and str(message.from_user.id) in ADMINS:
                await for_developers(message)
            elif message.text == '↩ Назад в главное меню':
                await UserState.previous()
                try:
                    if dictionary_to_use_in_this_function['id_of_block_of_photos_send_by_bot']:
                        for id in dictionary_to_use_in_this_function['id_of_block_of_photos_send_by_bot']:
                            try:
                                await bot.delete_message(message.chat.id, id)
                            except Exception:
                                pass
                        dictionary_to_use_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                    if dictionary_to_use_in_this_function['id_of_messages_about_bookmarks']:
                        for id in dictionary_to_use_in_this_function['id_of_messages_about_bookmarks']:
                            try:
                                await bot.delete_message(message.chat.id, id)
                            except Exception:
                                pass
                        dictionary_to_use_in_this_function['id_of_messages_about_bookmarks'] = []
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_id, str(dictionary_to_use_in_this_function), 2])).start()
                except Exception:
                    pass
                await start(message)
            elif message.text == '👮 Для правообладателей контента':
                await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id, chat_id=message.chat.id,
                                   text=await for_content_owners(message, bot_id),
                                   reply_markup=await get_reply_markup_for_user(message.from_user.id))
            elif message.text == '👨‍💻 Для пользователей':
                await send_message(user_id=message.from_user.id, bot=bot, bot_id=bot_id, chat_id=message.chat.id,
                                   text=await for_users(message, bot_id),
                                   reply_markup=await get_reply_markup_for_user(message.from_user.id),
                                   parse_mode='markdown')
            elif message.text:
                if '/gift' in message.text and str(message.from_user.id) in ADMINS:
                    await gift_pro_starter(message)
                elif '/unsubscribe' in message.text and str(message.from_user.id) in ADMINS:
                    await unsubscribe_from_pro_starter(message)
                else:
                    try:
                        await bot.delete_message(message.chat.id, message.message_id)
                    except Exception:
                        pass

    @dp.message_handler(state='*', content_types=['text'])
    async def handle_stupid_message(message: types.Message, state: FSMContext):
        if message.text == '↩ Назад в главное меню':
            await command_handler(message, state)
        else:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            except Exception:
                pass

    if not on_processing_advertisements_payments:
        if len(get_all_payments_data()) > 0:
            on_processing_advertisements_payments = True
            Thread(target=async_functions_process_starter, args=(process_payments, [])).start()
    t = Thread(target=async_functions_process_starter, args=(skip_updates_and_start_bot, [dp, token]))
    t.start()
    tokens[token]['thread'] = t


if __name__ == '__main__':
    try:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        working_bots_tokens = get_working_bots_tokens()
        print(f"{len(working_bots_tokens)} bot(s) connected to ReshenijaBot server!")
        for token in working_bots_tokens:
            bot_init(token)
        event_loop.create_task(reboot_daily_users(59))
        event_loop.run_forever()
    except KeyboardInterrupt:
        pass