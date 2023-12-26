from utils.database.folder_worker import get_dictionary
from utils.async_process_runner import start as async_functions_process_starter
from utils.database.folder_worker import create_or_dump_user


from threading import Thread
from math import ceil


# это функция, отвечающая за формирование валидного словаря всех номеров
async def producer(spisok, call, bot_id: int):
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
    

# функция для обрезки массива с кнопками, сделана для того, чтобы избежать ошибки tg api
async def buttons_validator(buttons):
    if len(buttons) > 98:
        buttons = buttons[:98]
    return buttons