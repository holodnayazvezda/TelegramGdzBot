import requests
from bs4 import BeautifulSoup

from data.config import HEADERS


async def get_solution_by_link_at_number(link_at_number: str) -> dict:
    r = requests.get(link_at_number, headers=HEADERS)
    if r.status_code == 200:
        try:
            soup = BeautifulSoup(markup=r.text, features='html.parser')
            task = None
            try:
                task = soup.find('p', class_='task-description').getText().strip()
            except Exception:
                pass
            if not isinstance(task, str):
                task = None
            image_links = list(map(lambda el: el.find('img').get('src'), soup.find_all('div', class_='with-overtask')))
            if not image_links:
                raise Exception
            return {'type': 1, 'data': image_links, 'task': task}
        except Exception:
            try:
                soup = BeautifulSoup(markup=r.text, features='html.parser')
                task = None
                try:
                    task = soup.find('p', class_='task-description').getText().strip()
                except Exception:
                    pass
                if not isinstance(task, str):
                    task = None
                solution_list_text_tags = list(map(lambda tag: tag.name, soup.find('div', class_='taskText').find_all(name=True)))
                solution_list_tags = []
                added_tags = []
                for tag_name in solution_list_text_tags:
                    if tag_name not in added_tags:
                        added_tags.append(tag_name)
                        text = list(filter(lambda el: el, list(map(lambda el: el.getText(), soup.find('div', class_='taskText').find_all(tag_name)))))
                        if text:
                            solution_list_tags += text
                return {'type': 2, 'data': '\n'.join(solution_list_tags), 'task': task}
            except Exception:
                return {'type': 0, 'data': [], 'task': None}
    else:
        return {'type': 0, 'data': [], 'task': None}
