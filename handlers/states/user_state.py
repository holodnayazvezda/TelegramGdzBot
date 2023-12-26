from aiogram.dispatcher.filters.state import StatesGroup, State


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