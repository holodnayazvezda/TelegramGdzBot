from aiogram import Bot, types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageNotModified

from utils.users.users import active_now
from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.database.database_worker import get_information_from
from utils.share.share_worker import get_save_data_id, save_shared_data
from utils.async_process_runner import start as async_functions_process_starter
from utils.aiogram_functions_worker import try_edit_or_send_message, send_message, send_photo, answer_callback_query
from utils.coder_and_decoder import decode_and_write
from utils.gdz.megaresheba_worker import get_solution_by_link_at_number
from handlers.states.user_state import UserState
from handlers.gdz.classes import gdz_starter
from handlers.gdz.gdz_functions import buttons_validator, producer
from handlers.bot import BotInfo


from threading import Thread


async def gdz_main_function(call: types.CallbackQuery, bot_instance: BotInfo, dictionary_to_use=None, state: FSMContext = None):
    if dictionary_to_use:
        dictionary_used_in_this_function = dictionary_to_use
    else:
        dictionary_used_in_this_function = await get_dictionary(str(call.from_user.id), bot_instance.bot_id, 2)
    if 'old_dict' not in dictionary_used_in_this_function:
        dictionary_used_in_this_function['old_dict'] = {}
    if 'id_of_messages_about_bookmarks' not in dictionary_used_in_this_function:
        dictionary_used_in_this_function['id_of_messages_about_bookmarks'] = []
    if dictionary_used_in_this_function['id_of_messages_about_bookmarks']:
        for id in dictionary_used_in_this_function['id_of_messages_about_bookmarks']:
            try:
                await bot_instance.bot.delete_message(call.message.chat.id, id)
            except Exception:
                pass
        dictionary_used_in_this_function['id_of_messages_about_bookmarks'] = []
        Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
    if dictionary_used_in_this_function:
        Thread(target=async_functions_process_starter, args=(active_now, [str(call.from_user.id), call.message.chat.id, bot_instance.bot_id])).start()
        try:
            if call.data == '⁉️ Найти решение':
                await gdz_starter(call, bot_instance)
            elif 'двз' in call.data or 'share' in call.data:
                # call.data = dictionary_used_in_this_function['current_key']
                bookmark_dict = {'key': dictionary_used_in_this_function['current_key'],
                                    'all_data': dictionary_used_in_this_function}
                if 'двз' in call.data:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton(text='❌ отмена', callback_data=bookmark_dict['key']))
                    await answer_callback_query(call, bot_instance.bot)
                    if ('id_of_block_of_photos_send_by_bot' in dictionary_used_in_this_function and
                            dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']):
                        for id in dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot']:
                            try:
                                await bot_instance.bot.delete_message(call.message.chat.id, id)
                            except Exception:
                                pass
                        dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                    try:
                        await bot_instance.bot.delete_message(chat_id=call.message.chat.id,
                                                    message_id=dictionary_used_in_this_function[
                                                        'id_of_message_with_markup'])
                    except Exception:
                        pass
                    dictionary_used_in_this_function['text_inputed'] = True
                    dictionary_used_in_this_function['bookmark_dict'] = bookmark_dict
                    message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                                chat_id=call.message.chat.id,
                                                                text='⬇️ Введите имя закладки',
                                                                reply_markup=markup)
                    dictionary_used_in_this_function['id_of_messages_about_bookmarks'].append(
                        message_id)  # к этому моменту значение по этому ключу точно будет!
                    dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                    # записать bookmark_dict в fsm
                    await UserState.bookmark_creation.set()
                    await state.update_data(bookmark_dict=bookmark_dict)
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
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
                                await bot_instance.bot.answer_callback_query(call.id, "Скопируй ссылку из сообщения!")
                            except Exception:
                                pass
                        else:
                            data_name = call.data.split("$")[1]
                            type_of_data = int(call.data.split("$")[2])  # 1 - книга, 2 - номер
                            id, success = await get_save_data_id(data_name, './data/databases/shared_data.sqlite3', "shared_data_ids")
                            if not success:
                                id = await save_shared_data(data_name, bookmark_dict, './data/databases/shared_data.sqlite3', 'shared_data')
                            link = f'https://t.me/{(await bot_instance.bot.get_me()).username}?start=shared_data{id}'
                            if type_of_data == 1:
                                await call.message.edit_caption(last_message_text + f'\n\n🔗 Поделись *этой ссылкой*, чтобы получить быстрый доступ к выбранному учебнику (номеру): `{link}`', parse_mode='markdown', reply_markup=call.message.reply_markup)
                            else:
                                await call.message.edit_text(last_message_text + f'\n\n🔗 Поделись *этой ссылкой*, чтобы получить быстрый доступ к выбранному учебнику (номеру): `{link}`', parse_mode='markdown', reply_markup=call.message.reply_markup)
                    except Exception as e:
                        print(e)
                        try:
                            await bot_instance.bot.answer_callback_query(call.id, "Непредвиденная ошибка! Попробуйте еще раз или поделитесь следующим номером")
                        except Exception:
                            pass
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
                    await answer_callback_query(call, bot_instance.bot)
                    message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                                chat_id=call.message.chat.id,
                                                                text=f'Выбери нужный предмет за {" ".join(dictionary_used_in_this_function["clas"].split()[1:])}',
                                                                message_id=call.message.message_id,
                                                                reply_markup=markup)
                    dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
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
                    await answer_callback_query(call, bot_instance.bot)
                    message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                                chat_id=call.message.chat.id,
                                                                text=f'Выбери автора твоей книги по выбранному предмету ({dictionary_used_in_this_function["subject"].lower()})',
                                                                message_id=call.message.message_id,
                                                                reply_markup=markup)
                    dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
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
                    await answer_callback_query(call, bot_instance.bot)
                    message_id = await send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                    chat_id=call.message.chat.id,
                                                    text=f'Выбери тип твоей книги по выбранному предмету ({dictionary_used_in_this_function["subject"].lower()})',
                                                    message_id=call.message.message_id, reply_markup=markup)
                    dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
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
                        await answer_callback_query(call, bot_instance.bot)
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
                        message_id = await send_photo(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
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
                            x = await bot_instance.bot.edit_message_text(chat_id=call.message.chat.id,
                                                            message_id=call.message.message_id,
                                                            text='🛑 Нам не удалось получить данные для выбранного решебника, рекомендуем посетить сайт https://megaresheba.ru для поиска решений номеров этого учебника',
                                                            reply_markup=markup)
                            dictionary_used_in_this_function['id_of_message_with_markup'] = x.message_id
                        except MessageNotModified:
                            pass
                        except Exception:
                            try:
                                await bot_instance.bot.delete_message(call.message.chat.id, call.message.message_id)
                            except Exception:
                                pass
                            x = await bot_instance.bot.send_message(chat_id=call.message.chat.id,
                                                        text='🛑 Нам не удалось получить данные для выбранного решебника, рекомендуем посетить сайт https://megaresheba.ru для поиска решений номеров этого учебника.',
                                                        reply_markup=markup)
                            dictionary_used_in_this_function['id_of_message_with_markup'] = x.message_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
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
                    to_check = await producer(dictionary_used_in_this_function['dict'][call.data], call, bot_instance.bot_id)
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
                                    await bot_instance.bot.delete_message(call.message.chat.id, id)
                                except Exception:
                                    pass
                            dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                        try:
                            try:
                                await bot_instance.bot.delete_message(call.message.chat.id, call.message.message_id)
                            except Exception:
                                pass
                            await answer_callback_query(call, bot_instance.bot)
                            message_id = \
                                await send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
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
                            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
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
                                    await bot_instance.bot.delete_message(call.message.chat.id, id)
                                except Exception:
                                    pass
                            dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                        try:
                            try:
                                await bot_instance.bot.delete_message(call.message.chat.id, call.message.message_id)
                            except Exception:
                                pass
                            await answer_callback_query(call, bot_instance.bot)
                            x = await bot_instance.bot.send_message(chat_id=call.message.chat.id,
                                                        text='К сожалению, мы не можем получить информацию для этого учебника, скорее всего он доступен только по подписке ;(',
                                                        reply_markup=markup)
                            dictionary_used_in_this_function['id_of_message_with_markup'] = x.message_id
                            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
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
                                await bot_instance.bot.delete_message(call.message.chat.id, id)
                            except Exception:
                                pass
                        dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                    try:
                        await bot_instance.bot.delete_message(call.message.chat.id, call.message.message_id)
                    except Exception:
                        pass
                    await answer_callback_query(call, bot_instance.bot)
                    if solution_data['type'] == 1:
                        images = []
                        for image in solution_data['data'][:10]:
                            images.append(types.InputMediaPhoto(media=image, parse_mode='html'))
                        z = await bot_instance.bot.send_media_group(chat_id=call.message.chat.id, media=images)
                        dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'].extend(
                            list(map(lambda el: el.message_id, z)))
                        if len(solution_data['data']) > 10:
                            if (not dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] or
                                    not isinstance(dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'], list)):
                                dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'] = []
                            for image in solution_data['data'][10:]:
                                message_id = await send_photo(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                                chat_id=call.message.chat.id, photo=image,
                                                                parse_mode="html", do_not_add_ads=True)
                                dictionary_used_in_this_function['id_of_block_of_photos_send_by_bot'].append(message_id)
                        if solution_data['task']:
                            message_text = f'📷 Фото запрашиваемого [задания ({dictionary_used_in_this_function["number"]})]({link_at_number}).\n📖 Текст задания: `{solution_data["task"]}`\n\nИсточник: https://megaresheba.ru'
                        else:
                            message_text = f'📷 Фото запрашиваемого [задания ({dictionary_used_in_this_function["number"]})]({link_at_number}).\n\nИсточник: https://megaresheba.ru'
                        message_id = await send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                        chat_id=call.message.chat.id,
                                                        text=message_text,
                                                        reply_markup=markup, parse_mode='markdown')
                    else:
                        if solution_data['task']:
                            message_text = f'📷 Ответ на запрашиваемое [задание ({dictionary_used_in_this_function["number"]})]({link_at_number}).\n📖 Текст задания: `{solution_data["task"]}`\n*{solution_data["data"]}*\n\nИсточник: https://megaresheba.ru'
                        else:
                            message_text = f'📷 Ответ на запрашиваемое [задание ({dictionary_used_in_this_function["number"]})]({link_at_number}).\n*{solution_data["data"]}*\nИсточник: https://megaresheba.ru'
                        message_id = await send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                        chat_id=call.message.chat.id,
                                                        text=message_text,
                                                        reply_markup=markup, parse_mode='markdown')
                    dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
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
                    await answer_callback_query(call, bot_instance.bot)
                    message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                                chat_id=call.message.chat.id,
                                                                text=f'Перейди по ссылке и получи решение своего номера! ({link_at_number[0][0]})',
                                                                message_id=call.message.message_id,
                                                                reply_markup=markup)
                    dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
            elif call.data == 'А почему не отправляются ?':
                try:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton(text='⏪ Назад',
                                                            callback_data=dictionary_used_in_this_function['number']))
                    await answer_callback_query(call, bot_instance.bot)
                    message_id = await try_edit_or_send_message(user_id=call.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                                chat_id=call.message.chat.id,
                                                                text='Если вы попали сюда, то либо произошла внутрення ошибка (вернитесь назад и повторите попытку), либо выбранный вами номер временно недоступен. В связи с этим, бот будет отпраялять вам ссылку, ведущую на сайт-источник. Перейдя по ней вы наудете решение на свой вопрос :) P.S. Создатель данного бота прилагает все усилия, для того, чтобы ускорить и упростить получения нужного ответа ! Если вы не можете получить фото нужного решения "на прямую" - это не моя вина!',
                                                                message_id=call.message.message_id,
                                                                reply_markup=markup)
                    dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
                    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(call.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
                except Exception:
                    pass
            else:
                print(f'Данные не найдены "{call.data}"')
        except Exception:
            pass