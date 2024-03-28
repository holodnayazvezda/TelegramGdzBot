import requests

from data.config import OCR_SPACE_API_KEYS
import data.config
from utils.chatgpt.requests_counter import *


async def get_text_from_image(user_id: int, image_url: str, timeout: int=None):
    try:
        ocr_data = requests.get(f"https://api.ocr.space/parse/imageurl?apikey={OCR_SPACE_API_KEYS[data.config.amount_of_requests_to_ocr_api % 15]}&url={image_url}&detectOrientation=True&filetype=JPG&OCREngine=2&isTable=False&scale=True", timeout)
        ocr_data = ocr_data.json()
        data.config.amount_of_requests_to_ocr_api += 1
        if not ocr_data['IsErroredOnProcessing']:
            message = ocr_data['ParsedResults'][0]['ParsedText']
            await increase_the_number_of_requests_for_the_user("./data/databases/quantity_of_requests.sqlite3",
                                                               "quantity_of_requests_to_ocr_space", user_id)
            return f"{message}"
        await increase_the_number_of_requests_for_the_user("./data/databases/quantity_of_requests.sqlite3",
                                                           "quantity_of_unsuccessful_requests_to_ocr_space", user_id)
    except Exception:
        await increase_the_number_of_requests_for_the_user("./data/databases/quantity_of_requests.sqlite3",
                                                           "quantity_of_unsuccessful_requests_to_ocr_space", user_id)
        return None
