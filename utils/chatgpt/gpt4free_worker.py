import asyncio
from threading import Thread

import g4f
import tiktoken

from data.config import get_max_tokens_in_response_for_user, COOKIES_FOR_GPT_4_BING_USERS, \
    COOKIES_FOR_GPT_4_BING_PRO_USERS
from utils.async_process_runner import start
from utils.chatgpt.chat_gpt_users_worker import *
from utils.chatgpt.chat_gpt_worker import ask_chat_gpt_and_return_answer
from utils.chatgpt.requests_counter import *
from utils.pro.pro_subscription_worker import is_pro


async def ask_chat_gpt_temporary_api(prompt: str, user_id: int) -> tuple[str, int]:
    history_of_requests = await get_history_of_requests("./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history",
                                                        user_id, await is_pro(user_id), "gpt-3.5-turbo")
    history_of_requests.append({'role': 'user', 'content': prompt})
    response_content = await g4f.ChatCompletion.create_async(
        model="gpt-3.5-turbo",
        messages=history_of_requests,
    )
    await add_request_to_history("./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history", user_id, prompt, 'user')
    await add_request_to_history("./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history", user_id, response_content, 'assistant')
    return response_content


async def ask_chat_gpt_4(prompt: str, user_id: int) -> tuple:
    tokens_in_response = len(tiktoken.encoding_for_model("gpt-3.5-turbo").encode(prompt)) + 7
    has_pro = await is_pro(user_id)
    history_of_requests = await get_history_of_requests("./data/databases/history_of_requests_to_chatgpt.sqlite3",
                                                        "users_history",user_id, has_pro, "gpt-4")
    history_of_requests.append({'role': 'user', 'content': prompt})
    if tokens_in_response > await get_max_tokens_in_response_for_user(has_pro):
        return None, 400
    try:
        response_content = await g4f.ChatCompletion.create_async(
            model="gpt-4",
            messages=history_of_requests,
            cookies=COOKIES_FOR_GPT_4_BING_PRO_USERS if has_pro else COOKIES_FOR_GPT_4_BING_USERS
        )
        await add_request_to_history("./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history",
                                     user_id, prompt, 'user')
        await add_request_to_history("./data/databases/history_of_requests_to_chatgpt.sqlite3", "users_history",
                                      user_id, response_content, 'assistant')
        Thread(target=start, args=(increase_the_number_of_requests_for_the_user,
                                   ["./data/databases/quantity_of_requests.sqlite3",
                                    'quantity_of_requests_to_gpt4_bing', user_id])).start()
        return response_content.replace('Bing', 'ReshenijaBotGpt'), 200
    except Exception:
        response_content, status_code = await ask_chat_gpt_and_return_answer('gpt-3.5-turbo', prompt, user_id)
        if status_code == 200:
            return response_content, status_code
        else:
            return None, status_code


async def main() -> None:
    response_content, status_code = await ask_chat_gpt_4("привет", 800)
    print(response_content, status_code)
            

if __name__ == '__main__':
    asyncio.run(main())
