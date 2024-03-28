from aiogram import types

from telebot.apihelper import ApiTelegramException
from telebot import TeleBot

from utils.aiogram_functions_worker import send_message_by_telebot, send_message
from utils.async_process_runner import start as async_functions_process_starter
from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.chatgpt.chat_gpt_users_worker import clear_history_of_requests
from utils.log.logging import log_info
from utils.pro.pro_subscription_worker import is_pro
from utils.chatgpt.chat_gpt_users_worker import get_amount_of_referrals, get_has_working_bots
from utils.chatgpt.chat_gpt_worker import get_amount_of_requests_for_user
from utils.ocr.image_worker import get_text_from_image
from utils.chatgpt.gpt4free_worker import ask_chat_gpt_temporary_api, ask_chat_gpt_4
from utils.chatgpt.chat_gpt_worker import ask_chat_gpt_and_return_answer
from utils.chatgpt.audio_to_text import audio_to_text
from utils.users.users import active_now
from data.config import get_available_amount_of_requests_to_chat_gpt, ADMINS
from handlers.bot import BotInfo
from handlers.states.user_state import UserState

import time
from threading import Thread
import os
import subprocess

# глобальная переменная задачи перебора пользователей
on_processing_chat_gpt_users = False
chats_ids_and_messages_for_chat_gpt_users = {}
# глобальная переменная для хранения текстов пользовательских сообщений и их id (chat gpt)
on_processing_chat_gpt_pro_users = False
chats_ids_and_messages_for_chat_gpt_pro_users = {}
# глобальная переменная для перебора рекламных объявлений
on_processing_advertisements_payments = False


def delete_messages(delay, chat_id: int, users_message_id: int, bots_message_id: int, bot_telebot: TeleBot) -> None:
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


async def unsuccessful_request_to_chatgpt(chat_id: int, user_id: int, message_text: str, bot_instance: BotInfo) -> None:
    try:
        response = await ask_chat_gpt_temporary_api(message_text, user_id)
        if response:
            send_message_by_telebot(user_id=user_id, bot_telebot=bot_instance.bot_telebot, bot_id=bot_instance.bot_id,
                                    chat_id=chat_id, text=response, parse_mode='markdown')
        else:
            raise Exception('The answer is empty')
    except Exception as e:
        log_info('gpt_errors.txt', f'unsuccessful chat gpt api error! {e}')
        send_message_by_telebot(user_id=user_id, bot_telebot=bot_instance.bot_telebot, bot_id=bot_instance.bot_id,
                                chat_id=chat_id,
                                text='🛑 Возникла ошибка при получении ответа! Повторите попытку через несколько минут.')


async def generate_and_send_answer(chat_id: int, user_id: int, message_text: str, bot_instance: BotInfo) -> None:
    bot_instance.bot_telebot.send_chat_action(chat_id=chat_id, action='typing')
    dictionary_used_in_this_function = await get_dictionary(str(user_id), bot_instance.bot_id, 2)
    try:
        model = 'gpt-3.5-turbo'
        if 'selected_model' in dictionary_used_in_this_function and dictionary_used_in_this_function['selected_model']:
            model = dictionary_used_in_this_function['selected_model']
            log_info('chatgpt_use_history.txt', model)
        if model == 'gpt-4-bing':
            response = await ask_chat_gpt_4(prompt=message_text, user_id=user_id)
        else:
            response = await ask_chat_gpt_and_return_answer(model, prompt=message_text, user_id=user_id)
        if response[1] == 200:
            send_message_by_telebot(user_id=user_id, bot_telebot=bot_instance.bot_telebot, bot_id=bot_instance.bot_id,
                                    chat_id=chat_id, text=response[0], parse_mode='markdown')
            Thread(target=async_functions_process_starter, args=(create_or_dump_user,
                                                                 [str(user_id), bot_instance.bot_id,
                                                                  str(dictionary_used_in_this_function), 2])).start()
        else:
            if response[1] == 400:
                send_message_by_telebot(user_id=user_id, bot_telebot=bot_instance.bot_telebot,
                                        bot_id=bot_instance.bot_id, chat_id=chat_id,
                                        text="⚠️ Ваш запрос слишком длинный! Пожалуйста, сократите запрос, что бы бот смог обработать его.",
                                        parse_mode='markdown')
            else:
                await unsuccessful_request_to_chatgpt(chat_id, user_id, message_text, bot_instance)
    except Exception:
        await unsuccessful_request_to_chatgpt(chat_id, user_id, message_text, bot_instance)


async def clear_chat_gpt_conversation(message, bot_instance: BotInfo):
    Thread(target=async_functions_process_starter, args=(clear_history_of_requests,
                                                         ['./data/databases/history_of_requests_to_chatgpt.sqlite3',
                                                          'users_history', message.from_user.id])).start()
    await bot_instance.bot.send_message(chat_id=message.chat.id, text="✅ История диалога с ChatGPT очищена")


async def add_user_to_queue_and_start_generating(message: types.Message, bot_instance: BotInfo) -> None:
    global on_processing_chat_gpt_users, chats_ids_and_messages_for_chat_gpt_users, \
        on_processing_chat_gpt_pro_users, chats_ids_and_messages_for_chat_gpt_pro_users
    dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 2)
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
    users_data = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 1)
    has_working_bots = await get_has_working_bots(message.from_user.id, bot_instance.bot_id, users_data)
    amount_of_referrals = await get_amount_of_referrals(message.from_user.id, bot_instance.bot_id, users_data)
    if (await get_amount_of_requests_for_user("./data/databases/quantity_of_requests.sqlite3", table_name,
                                              message.from_user.id) <
            await get_available_amount_of_requests_to_chat_gpt(has_pro, model, has_working_bots, amount_of_referrals)):
        if message.content_type == 'text':
            if model == 'gpt-4-bing':
                if has_pro:
                    chats_ids_and_messages_for_chat_gpt_pro_users[message.chat.id] = [message.from_user.id,
                                                                                      message.text]
                    if on_processing_chat_gpt_pro_users is False:
                        on_processing_chat_gpt_pro_users = True
                        Thread(target=async_functions_process_starter, args=(process_chat_gpt_pro_users,
                                                                             [bot_instance])).start()
                else:
                    chats_ids_and_messages_for_chat_gpt_users[message.chat.id] = [message.from_user.id,
                                                                                  message.text]
                    if on_processing_chat_gpt_users is False:
                        on_processing_chat_gpt_users = True
                        Thread(target=async_functions_process_starter, args=(process_chat_gpt_users,
                                                                             [bot_instance])).start()
            else:
                await generate_and_send_answer(message.chat.id, message.from_user.id, message.text, bot_instance)
        elif message.content_type == 'voice':
            if has_pro:
                try:
                    Thread(target=async_functions_process_starter,
                           args=(translate_audio_to_text_and_start_generating,
                                 [message, await (await message.voice.get_file()).download(), has_pro, model,
                                  bot_instance])).start()
                except Exception:
                    pass
            else:
                message_id = await send_message(user_id=message.from_user.id, bot=bot_instance.bot,
                                                bot_id=bot_instance.bot_id, chat_id=message.chat.id,
                                                text='⚠️ Функция отправки запроса Chat GPT голосовым сообщением доступна *только для подписчиков 💎 ReshenijaBot PRO*! Приобрести подписку вы можете в *личном кабинете*.',
                                                parse_mode='markdown')
                Thread(target=delete_messages, args=(7, message.chat.id, message.message_id, message_id,
                                                     bot_instance.bot_telebot)).start()
                return
        elif message.content_type == 'photo':
            if message.media_group_id:
                dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_instance.bot_id,
                                                                        2)
                if ('last_chat_gpt_photo_media' in dictionary_used_in_this_function and
                        message.media_group_id == dictionary_used_in_this_function['last_chat_gpt_photo_media']):
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    return
                dictionary_used_in_this_function['last_chat_gpt_photo_media'] = message.media_group_id
                Thread(target=async_functions_process_starter, args=(create_or_dump_user,
                                                                     [str(message.from_user.id), bot_instance.bot_id,
                                                                      str(dictionary_used_in_this_function),
                                                                      2])).start()
            try:
                Thread(target=async_functions_process_starter,
                       args=(get_text_from_image_and_start_generating,
                             [message, (await message.photo[-1].get_file()).file_path, model, bot_instance])).start()
            except Exception:
                pass
    else:
        users_data = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 1)
        has_working_bots = await get_has_working_bots(message.from_user.id, bot_instance.bot_id, users_data)
        amount_of_referrals = await get_amount_of_referrals(message.from_user.id, bot_instance.bot_id, users_data)
        message_text = f'❗️ К сожалению, вы достигли *дневного лимита в {await get_available_amount_of_requests_to_chat_gpt(has_pro, model, has_working_bots, amount_of_referrals)} запросов к модели {model}*! Это ограничение необходимо для поддержания корректной работы и высокой скорости ответа бота. {model.capitalize()} снова сможет отвечать на ваши вопросы *после 00:00 по МСК*.'
        if not has_pro:
            message_text += '\n\n💯 Если вы хотите *увеличить лимит на количество запросов к Chat GPT*, оформите подписку 💎 ReshenijaBot PRO! Вы можете это сделать в *личном кабинете*.'
        message_id = await send_message(user_id=message.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                        chat_id=message.chat.id,
                                        text=message_text,
                                        parse_mode='markdown')
        Thread(target=delete_messages, args=(20, message.chat.id, message.message_id, message_id,
                                             bot_instance.bot_telebot)).start()


async def get_text_from_image_and_start_generating(message: types.Message, filepath, model: str,
                                                   bot_instance: BotInfo) -> None:
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
        bot_instance.bot_telebot.send_chat_action(chat_id=message.chat.id, action='upload_photo')
        image_url = f'https://api.telegram.org/file/bot{bot_instance.token}/{filepath}'
        data = await get_text_from_image(message.from_user.id, image_url, 15)
        if data:
            if model == 'gpt-4-bing':
                if await is_pro(message.from_user.id):
                    chats_ids_and_messages_for_chat_gpt_pro_users[message.chat.id] = [message.from_user.id, data]
                    if on_processing_chat_gpt_pro_users is False:
                        on_processing_chat_gpt_pro_users = True
                        Thread(target=async_functions_process_starter, args=(process_chat_gpt_pro_users,
                                                                             [bot_instance])).start()
                else:
                    chats_ids_and_messages_for_chat_gpt_users[message.chat.id] = [message.from_user.id, data]
                    if on_processing_chat_gpt_users is False:
                        on_processing_chat_gpt_users = True
                        Thread(target=async_functions_process_starter, args=(process_chat_gpt_users,
                                                                             [bot_instance])).start()
            else:
                await generate_and_send_answer(message.chat.id, message.from_user.id, data, bot_instance)
        else:
            message_id = send_message_by_telebot(user_id=message.from_user.id, bot_telebot=bot_instance.bot_telebot,
                                                 bot_id=bot_instance.bot_id, chat_id=message.chat.id,
                                                 text='🛑 Не удалось распознать текст с изображения, пожалуйста, попробуйте отправить другое изображение.',
                                                 parse_mode='markdown')
            Thread(target=delete_messages, args=(5, message.chat.id, message.message_id, message_id,
                                                 bot_instance.bot_telebot)).start()
    else:
        if amount_of_requests_to_ocr_api <= available_amount_of_requests_to_ocr_api:
            message_text = f'❗️ К сожалению, вы достигли дневного лимита в {available_amount_of_requests_to_ocr_api} отправок изображений к ChatGPT. Вы вновь сможете отправить ChatGPT запрос изображением *после 00:00 по МСК*!'
            if not has_pro:
                message_text = f'{message_text} 💯 Если вы хотите увеличить лимит до *50 запросов в день*, оформите подписку 💎 ReshenijaBot PRO! Вы можете это сделать в *личном кабинете*.'
            message_id = send_message_by_telebot(user_id=message.from_user.id, bot_telebot=bot_instance.bot_telebot,
                                                 bot_id=bot_instance.bot_id,
                                                 chat_id=message.chat.id,
                                                 text=message_text,
                                                 parse_mode='markdown')
        else:
            message_id = send_message_by_telebot(user_id=message.from_user.id, bot_telebot=bot_instance.bot_telebot,
                                                 bot_id=bot_instance.bot_id,
                                                 chat_id=message.chat.id,
                                                 text='⚠️ Количество ошибок при распознавании текста с изображений достигло 35. Попробуйте еще раз *после 00:00 по МСК*!',
                                                 parse_mode='markdown')
        Thread(target=delete_messages, args=(20, message.chat.id, message.message_id, message_id,
                                             bot_instance.bot_telebot)).start()


async def translate_audio_to_text_and_start_generating(message: types.Message, downloaded_message_file, has_pro: bool,
                                                       model: str, bot_instance: BotInfo) -> None:
    global on_processing_chat_gpt_users, chats_ids_and_messages_for_chat_gpt_users, \
        on_processing_chat_gpt_pro_users, chats_ids_and_messages_for_chat_gpt_pro_users
    voice_file_path_oga, voice_file_path_wav = None, None
    try:
        bot_instance.bot_telebot.send_chat_action(chat_id=message.chat.id, action='upload_voice')
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
                    Thread(target=async_functions_process_starter, args=(process_chat_gpt_pro_users,
                                                                         [bot_instance])).start()
            else:
                if on_processing_chat_gpt_users is False:
                    on_processing_chat_gpt_users = True
                    Thread(target=async_functions_process_starter, args=(process_chat_gpt_users,
                                                                         [bot_instance])).start()
        else:
            await generate_and_send_answer(message.chat.id, message.from_user.id, data, bot_instance)
    except Exception as e:
        if 'The length of the audiofile is more that 90 seconds' in str(e):
            message_text = '⚠️ Длинна голосового сообщения превышает 1.5 минуты! Оно не может быть обработано.'
        elif 'The weight of the audiofile is more that 5M' in str(e):
            message_text = \
                '⚠️ Вес голосового сообщения не может превышать 5 мегабайт! Оно не может быть обработано.'
        else:
            message_text = '🛑 Не удалось распознать текст голосового сообщения, пожалуйста, попробуйте еще раз.'
        message_id = send_message_by_telebot(user_id=message.from_user.id, bot_telebot=bot_instance.bot_telebot,
                                             bot_id=bot_instance.bot_id, chat_id=message.chat.id, text=message_text)
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
        Thread(target=delete_messages, args=(5, message.chat.id, message.message_id, message_id,
                                             bot_instance.bot_telebot)).start()


async def process_chat_gpt_users(bot_instance: BotInfo) -> None:
    global on_processing_chat_gpt_users, chats_ids_and_messages_for_chat_gpt_users
    while True:
        for chat_id, message_data in list(chats_ids_and_messages_for_chat_gpt_users.items()):
            del chats_ids_and_messages_for_chat_gpt_users[chat_id]
            await generate_and_send_answer(chat_id, message_data[0], message_data[1], bot_instance)
        if len(chats_ids_and_messages_for_chat_gpt_users) == 0:
            on_processing_chat_gpt_users = False
            return


async def process_chat_gpt_pro_users(bot_instance: BotInfo) -> None:
    global on_processing_chat_gpt_pro_users, chats_ids_and_messages_for_chat_gpt_pro_users
    while True:
        for chat_id, message_data in list(chats_ids_and_messages_for_chat_gpt_pro_users.items()):
            del chats_ids_and_messages_for_chat_gpt_pro_users[chat_id]
            await generate_and_send_answer(chat_id, message_data[0], message_data[1], bot_instance)
        if len(chats_ids_and_messages_for_chat_gpt_pro_users) == 0:
            on_processing_chat_gpt_pro_users = False
            return


async def change_gpt_version(message: types.Message, bot_instance: BotInfo) -> None:
    Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), message.chat.id,
                                                                      bot_instance.bot_id])).start()
    dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 2)
    users_data = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 1)
    has_working_bots = await get_has_working_bots(message.from_user.id, bot_instance.bot_id, users_data)
    amount_of_referrals = await get_amount_of_referrals(message.from_user.id, bot_instance.bot_id, users_data)
    selected_model = 'gpt-4-bing' if 'gpt-4' in message.text else 'gpt-3.5-turbo'
    dictionary_used_in_this_function['selected_model'] = selected_model
    has_pro = await is_pro(message.from_user.id)
    if selected_model == 'gpt-4-bing':
        table_name = 'quantity_of_requests_to_gpt4_bing'
    else:
        table_name = 'quantity_of_requests_to_gpt3'
    available_amount_of_requests = await get_available_amount_of_requests_to_chat_gpt(has_pro, selected_model,
                                                                                      has_working_bots,
                                                                                      amount_of_referrals)
    amount_of_requests = await get_amount_of_requests_for_user('./data/databases/quantity_of_requests.sqlite3',
                                                               table_name, message.from_user.id)
    rest_of_requests = available_amount_of_requests - amount_of_requests
    message_text = f'✅ Вы переключились на модель: *{selected_model}*.\n\n'
    if rest_of_requests:
        message_text += f'⏳ Сегодня вы можете задать ей вопрос еще *{rest_of_requests} раз(а)*.'
        if has_pro:
            message_text += f'\n\n💎 Вы являетесь подписчиком ReshenijaBot PRO, поэтому ваш увеличенный лимит для выбранной модели составляет *{available_amount_of_requests}* запросов в день.'
        else:
            message_text += f'\n\nℹ️ Ваш лимит для выбранной модели составляет *{available_amount_of_requests}* запросов в день.'
        await UserState.chat_gpt_writer.set()
    else:
        message_text += f'❗️ Вы достигли дневного лимита в {available_amount_of_requests} запросов к выбранной модели. Она вновь сможет отвечать на ваши запросы завтра.'
        if not has_pro:
            message_text += f'\n\n 💯 Чтобы увеличить лимит до {await get_available_amount_of_requests_to_chat_gpt(True, selected_model, has_working_bots, amount_of_referrals)} запросов в день, подключите PRO подписку в личном кабинете.'
    chatgpt_main_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    chatgpt_main_markup.add(types.KeyboardButton(text='🗑 Очистить историю диалога'))
    chatgpt_main_markup.add(types.KeyboardButton(text=f"🔁 Переключиться на {'gpt-4' if selected_model == 'gpt-3.5-turbo' else 'gpt-3.5-turbo'}"))
    chatgpt_main_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
    await bot_instance.bot.send_message(chat_id=message.chat.id, text=message_text, reply_markup=chatgpt_main_markup,
                                        parse_mode='markdown')
    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id),
                                                                               bot_instance.bot_id,
                                                                               str(dictionary_used_in_this_function),
                                                                               2])).start()
    