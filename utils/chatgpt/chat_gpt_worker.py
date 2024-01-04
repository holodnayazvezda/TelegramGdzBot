import asyncio

import openai
import tiktoken
from threading import Thread

from utils.chatgpt.requests_counter import *
from utils.chatgpt.chat_gpt_users_worker import *
from utils.chatgpt.apikeys_worker import start_or_stop_api_key, update_api_keys
from data.config import get_max_tokens_in_response_for_user
from utils.pro.pro_subscription_worker import is_pro
from utils.async_process_runner import start
from utils.chatgpt.apikeys_worker import counter_of_requests


async def ask_chat_gpt_and_return_answer(model: str, prompt: str, user_id: int, recursion_len: int = 0) -> tuple:
    tokens_in_response = len(tiktoken.encoding_for_model("gpt-3.5-turbo").encode(prompt)) + 7
    global counter_of_requests
    from apikeys_worker import OPENAI_API_KEYS, SHUTTLEAI_API_KEYS
    has_pro = await is_pro(user_id)
    history_of_requests = await get_history_of_requests("./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history",
                                                        user_id, has_pro, model)
    history_of_requests.append({'role': 'user', 'content': prompt})
    if tokens_in_response > await get_max_tokens_in_response_for_user(has_pro):
        return None, 400
    if model == 'gpt-4-bing':
        table_name = 'quantity_of_requests_to_gpt4_bing'
    else:
        table_name = 'quantity_of_requests_to_gpt3'
    if model == 'gpt-4-bing':
        model = 'gpt-4'
        api_key = SHUTTLEAI_API_KEYS[counter_of_requests % len(SHUTTLEAI_API_KEYS)]
        openai.api_base = 'https://api.shuttleai.app/v1'
        temperature = 0.8
    else:
        api_key = OPENAI_API_KEYS[counter_of_requests % len(OPENAI_API_KEYS)]
        openai.api_base = 'https://api.openai.com/v1'
        temperature = 0.2 if has_pro else 0.1
    openai.api_key = api_key
    counter_of_requests += 1
    try:
        Thread(target=start, args=(add_request_to_history, ["./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history",
                                                            user_id, prompt, 'user'])).start()
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=history_of_requests,
            temperature=temperature
        )
        response_content = response.choices[0].message.content
        Thread(target=start, args=(add_request_to_history, ["./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history",
                                                            user_id, response_content, 'assistant'])).start()
        Thread(target=start, args=(increase_the_number_of_requests_for_the_user, ["./data/databases/quantity_of_requests.sqlite3",
                                                                                  table_name, user_id])).start()
        return response_content.replace('ShuttleAi', 'ReshenijaBotAi').replace("ShuttleAI", "ReshenijaBotAi").replace("\\n", "").strip(), 200
    except Exception as e:
        print(e)
        if 'gpt-4' in model:
            return await ask_chat_gpt_and_return_answer('gpt-3.5-turbo', prompt, user_id)
        if 'exceeded' in str(e) and 'quota' in str(e) and 'check' in str(e) and 'plan' in str(e):
            if api_key.startswith('nv'):
                provider = 2
            else:
                provider = 1
            Thread(target=start, args=(start_or_stop_api_key, [provider, api_key, 0])).start()
            await update_api_keys()
            if recursion_len >= 3:
                return None, 429
            else:
                await ask_chat_gpt_and_return_answer(model, prompt, user_id, recursion_len + 1)
        elif 'maximum' in str(e) and 'context' in str(e) and 'length' in str(e) and 'tokens' in str(e):
            Thread(target=start, args=(clear_history_of_requests, ["./data/databases/history_of_requests_to_chatgpt.sqlite3",
                                                                   "users_history", user_id])).start()
            if recursion_len >= 3:
                return None, 429
            else:
                await ask_chat_gpt_and_return_answer(model, prompt, user_id, recursion_len + 1)
        else:
            return None, 500


if __name__ == '__main__':
    asyncio.run(ask_chat_gpt_and_return_answer("gpt-3.5-turbo", "привет", 112))