async def ads_status_to_text(ads_status: int) -> str:
    if ads_status == 1:
        return '🛡 На модерации'
    elif ads_status == 2:
        return '❌ Не прошло модерацию'
    elif ads_status == 3:
        return '💳 Ожидает оплату'
    elif ads_status == 4:
        return '⏳ Выполняется'
    elif ads_status == 5:
        return '✅ Выполнен'


async def status_code_to_menu_text(ads_status) -> str:
    if ads_status:
        if ads_status == 1:
            return '🛡 На модерации'
        elif ads_status == 2:
            return '❌ Не прошли модерацию'
        elif ads_status == 3:
            return '💳 Ожидают оплату'
        elif ads_status == 4:
            return '⏳ Выполняются'
        elif ads_status == 5:
            return '✅ Выполнены'
    else:
        return '💠 Все'