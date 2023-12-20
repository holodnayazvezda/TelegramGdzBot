from data.config import PAYMENTS_YOOMONEY_TOKEN
from yoomoney import Client, Quickpay


async def get_payment_link(label: str, price, type_of_purchase: int):
    if type_of_purchase == 1:
        targets = 'Оплатите этот счет, чтобы запустить показы вашего рекламного объявления'
    else:
        targets = 'Оплатите это счет, чтобы получить подписку ReshenijaBot Pro на 1 месяц!'
    quickpay = Quickpay(
        receiver="4100118315446381",
        quickpay_form="shop",
        targets=targets,
        paymentType="SB",
        sum=float(price),
        label=label
    )
    return quickpay.redirected_url


async def check_payment(label: str):
    client = Client(PAYMENTS_YOOMONEY_TOKEN)
    history = client.operation_history(label=label)
    if history.operations:
        return True
    else:
        return False
