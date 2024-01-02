import base64
from os import remove

import requests


async def get_response_code_and_write(link: str) -> str: 
    r = requests.get(link)
    img = open('image.jpg', 'wb')
    img.write(r.content)
    img.close()
    # открыли и прочитали img
    with open('image.jpg', 'rb') as f:
        data = f.read()
        f.close()
    # записали прочитанный контент в кодировки base64
    try:
        remove('image.jpg')
    except:
        pass
    return(str(base64.b64encode(data)))


async def decode_and_write(content) -> bytes:
    img_data = base64.b64decode(eval(content))
    return img_data
