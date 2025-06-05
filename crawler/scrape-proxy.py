import requests
from bs4 import BeautifulSoup
import json
import re
import random
import time
from urllib.parse import urljoin
import os
from dotenv import load_dotenv

# Загрузка настроек из .env
load_dotenv()

# Получение настроек
SLEEP_BETWEEN_REQUESTS = float(os.getenv('SLEEP_BETWEEN_REQUESTS', 1.5))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
PROXY_LIST = os.getenv('PROXY_LIST', '').split(',') if os.getenv('PROXY_LIST') else []


def get_random_proxy():
    """Возвращает случайный прокси из списка или None, если список пуст."""
    return random.choice(PROXY_LIST) if PROXY_LIST else None


def fetch_page_content(url, retries=0):
    """Загружает содержимое страницы с использованием прокси и повторными попытками."""
    proxy = get_random_proxy()
    proxies = {'http': proxy, 'https': proxy} if proxy else None

    try:
        response = requests.get(url, timeout=30, proxies=proxies)
        response.raise_for_status()
        time.sleep(SLEEP_BETWEEN_REQUESTS)  # Задержка между запросами
        return response.text
    except requests.RequestException as e:
        print(f"Ошибка при загрузке {url} (прокси: {proxy}): {e}")
        if retries < MAX_RETRIES:
            print(f"Повторная попытка {retries + 1}/{MAX_RETRIES} для {url}")
            time.sleep(SLEEP_BETWEEN_REQUESTS * (retries + 1))
            return fetch_page_content(url, retries + 1)
        return None


def parse_diseases(url):
    html_content = fetch_page_content(url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    diseases = []

    for section in soup.find_all(['div', 'section'], class_=re.compile('disease|item|content')):
        title = section.find(['h2', 'h3', 'span'], class_=re.compile('title|name'))
        description = section.find(['p', 'div'], class_=re.compile('description|text'))
        link = section.find('a', href=True)

        if title and description:
            disease = {
                'name': title.get_text(strip=True),
                'description': description.get_text(strip=True),
                'detail_url': urljoin(url, link['href']) if link else url
            }
            diseases.append(disease)

    return diseases


def parse_pests(url):
    html_content = fetch_page_content(url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    pests = []

    for section in soup.find_all(['div', 'section'], class_=re.compile('pest|item|content')):
        title = section.find(['h2', 'h3', 'span'], class_=re.compile('title|name'))
        description = section.find(['p', 'div'], class_=re.compile('description|text'))
        link = section.find('a', href=True)

        if title and description:
            pest = {
                'name': title.get_text(strip=True),
                'description': description.get_text(strip=True),
                'detail_url': urljoin(url, link['href']) if link else url
            }
            pests.append(pest)

    return pests


def parse_weeds(url):
    html_content = fetch_page_content(url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    weeds = []

    for section in soup.find_all(['div', 'section'], class_=re.compile('weed|item|content')):
        title = section.find(['h2', 'h3', 'span'], class_=re.compile('title|name'))
        scientific_name = section.find(['p', 'span'], class_=re.compile('scientific|latin'))
        link = section.find('a', href=True)

        if title:
            weed = {
                'name': title.get_text(strip=True),
                'scientific_name': scientific_name.get_text(strip=True) if scientific_name else '',
                'detail_url': urljoin(url, link['href']) if link else url
            }
            weeds.append(weed)

    return weeds


def main():
    base_url = 'https://betaren.ru'
    urls = {
        'diseases': f'{base_url}/harmful/bolezni/',
        'pests': f'{base_url}/harmful/vrediteli/',
        'weeds': f'{base_url}/harmful/sornyaki/'
    }

    data = {
        'diseases': {
            'cereals': parse_diseases(f'{base_url}/harmful/bolezni/bolezni-zernovykh-kultur/'),
            'rapeseed': parse_diseases(f'{base_url}/harmful/bolezni/bolezni-rapsa/'),
            'corn': parse_diseases(f'{base_url}/harmful/bolezni/bolezni-kukuruzy/')
        },
        'pests': {
            'cereals': parse_pests(f'{base_url}/harmful/vrediteli/vrediteli-zernovykh-kultur/'),
            'rapeseed': parse_pests(f'{base_url}/harmful/vrediteli/vrediteli-rapsa/'),
            'corn': parse_pests(f'{base_url}/harmful/vrediteli/vrediteli-kukuruzy/')
        },
        'weeds': parse_weeds(urls['weeds'])
    }

    with open('betaren_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("Данные успешно сохранены в betaren_data.json")


if __name__ == "__main__":
    main()