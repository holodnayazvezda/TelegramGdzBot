from aiogram import types, Bot

from telebot import TeleBot

from threading import Thread
from utils.async_process_runner import start as async_functions_process_starter
from utils.users.users import active_now
from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.pro.pro_subscription_worker import is_pro
from utils.chatgpt.requests_counter import get_amount_of_requests_for_user
from utils.aiogram_functions_worker import send_message, try_edit_or_send_message
from handlers.gpt.gpt_functions import change_gpt_version, generate_and_send_answer, clear_chat_gpt_conversation, add_user_to_queue_and_start_generating
from data.config import get_max_tokens_in_response_for_user, ADMINS
from handlers.states.user_state import UserState
from handlers.bot import BotInfo
from handlers.start.start_handler import start


async def chat_gpt_messages_handler(message: types.Message, bot_instance: BotInfo) -> None:
    if message.text == '↩ Назад в главное меню':
        await start(message, bot_instance)
    elif message.text == '🗑 Очистить историю диалога':
        await clear_chat_gpt_conversation(message, bot_instance)
    elif message.text in ['🔁 Переключиться на gpt-4',  '🔁 Переключиться на gpt-3.5-turbo']:
        await change_gpt_version(message, bot_instance)
    else:
        await generate_and_send_answer(message.chat.id, message.from_user.id, message.text, bot_instance)


async def chat_gpt_starter(message, bot_instance: BotInfo) -> None:
    if isinstance(message, types.Message):
        chat_id = message.chat.id
    else:
        chat_id = message.message.chat.id
    Thread(target=async_functions_process_starter, args=(active_now, [str(message.from_user.id), chat_id, bot_instance.bot_id])).start()
    dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 2)
    try:
        model = dictionary_used_in_this_function['selected_model']
    except KeyError:
        model = 'gpt-3.5-turbo'
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
    if ('id_of_message_with_markup' not in dictionary_used_in_this_function or not
    dictionary_used_in_this_function['id_of_message_with_markup']):
        chatgpt_main_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        chatgpt_main_markup.add(types.KeyboardButton(text='🗑 Очистить историю диалога'))
        chatgpt_main_markup.add(types.KeyboardButton(text=f"🔁 Переключиться на {'gpt-4' if (model == 'gpt-3.5-turbo' or not model) else 'gpt-3.5-turbo'}"))
        chatgpt_main_markup.add(types.KeyboardButton(text='↩ Назад в главное меню'))
        await send_message(user_id=message.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id, chat_id=chat_id, text='🟢',
                            reply_markup=chatgpt_main_markup, do_not_add_ads=True)
        message_id = await send_message(user_id=message.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                        chat_id=chat_id,
                                        text=text, parse_mode='markdown')
    else:
        message_id = await try_edit_or_send_message(user_id=message.from_user.id, bot=bot_instance.bot, bot_id=bot_instance.bot_id,
                                                    chat_id=chat_id,
                                                    text=text,
                                                    message_id=dictionary_used_in_this_function[
                                                        'id_of_message_with_markup'],
                                                    parse_mode='markdown')
    dictionary_used_in_this_function['id_of_message_with_markup'] = message_id
    Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
    await UserState.chat_gpt_worker.set()


async def chat_gpt_task_handler(message: types.Message, bot_instance: BotInfo) -> None:
    dictionary_used_in_this_function = await get_dictionary(str(message.from_user.id), bot_instance.bot_id, 2)
    if message.text == '↩ Назад в главное меню':
        await start(message, bot_instance)
    elif message.text == '🗑 Очистить историю диалога':
        await clear_chat_gpt_conversation(message, bot_instance)
    elif message.text in ['🔁 Переключиться на gpt-4',  '🔁 Переключиться на gpt-3.5-turbo']:
        await change_gpt_version(message, bot_instance)
    else:
        try:
            Thread(target=async_functions_process_starter, args=(create_or_dump_user, [str(message.from_user.id), bot_instance.bot_id, str(dictionary_used_in_this_function), 2])).start()
            await add_user_to_queue_and_start_generating(message, bot_instance)
        except Exception as e:
            try:
                await bot_instance.bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass