import re


async def string_validator(string):
    if len(string.encode('utf-8')) > 61:
        while len(string.encode('utf-8')) > 61:
            string = string[:-1]
        string += '...'
    return string


async def encoded_image_and_links_validator(image_list):
    itog_list = []
    for i in range(len(image_list)):
        if 'https:' not in image_list[i] and 'megaresheba.ru/attachments' not in image_list[i]:
            if i == 0:
                return image_list
            itog_list.append(image_list[i])
            break
    for image in image_list:
        if image.startswith('https://megaresheba.ru/attachments'):
            itog_list.append(image)
    return itog_list


def contains_only_allowed_chars(input_string):
    pattern = r"""[^a-z A-Zа-яА-ЯёЁ0123456789.,!?;:^%|*&()$€₽£¥₺₴₸₿฿₵₡₢₣₲₴₾₤₣₰₣₳₢₭₮₱₲₥₦₩₫₯₠₣₹₨₮₱₪'"/\\s#~{}÷×+_-]"""
    matches = re.findall(pattern, input_string)
    return not bool(matches)
