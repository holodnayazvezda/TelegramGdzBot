from random import randint
from threading import Thread

from utils.database.folder_worker import get_dictionary, create_or_dump_user
from utils.advertisements.ads_database_worker import get_paid_ads, add_watcher
from utils.pro.pro_subscription_worker import is_pro
from utils.async_process_runner import start


async def get_ads_for_user(user_id: int, bot_id: int, return_none: bool):
    if not await is_pro(user_id) and not return_none:
        users_data = await get_dictionary(str(user_id), bot_id, 1)
        paid_ads_data = await get_paid_ads()
        if not paid_ads_data:
            return None
        try:
            paid_ads_unviewed_by_user = list(filter(lambda el: el not in users_data['watched_ads_ids']
                                                    and paid_ads_data[el][0] != user_id, paid_ads_data))
        except Exception:
            paid_ads_unviewed_by_user = list(filter(lambda el: paid_ads_data[el][0] != user_id, paid_ads_data))
        if paid_ads_unviewed_by_user:
            ads_id = paid_ads_unviewed_by_user[randint(0, len(paid_ads_unviewed_by_user) - 1)]
        else:
            paid_ads_data_ids = list(filter(lambda el: paid_ads_data[el][0] != user_id, paid_ads_data))
            if paid_ads_data_ids:
                ads_id = min(paid_ads_data_ids, key=lambda el: users_data['watched_ads_ids'][el])
            else:
                return None
        return ads_id, paid_ads_data[ads_id]
    return None


async def view_ads_by_user(user_id: int, bot_id: int, ads_id: int):
    await add_watcher(ads_id)
    users_data = await get_dictionary(str(user_id), bot_id, 1)
    if 'watched_ads_ids' in users_data:
        if ads_id in users_data['watched_ads_ids']:
            users_data['watched_ads_ids'][ads_id] += 1
        else:
            users_data['watched_ads_ids'][ads_id] = 1
    else:
        users_data['watched_ads_ids'] = {ads_id: 1}
    Thread(target=start, args=(create_or_dump_user, [str(user_id), bot_id, str(users_data), 1])).start()
