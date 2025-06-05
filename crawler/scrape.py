import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Настройка логирования
logging.basicConfig(
    filename='scrape_betaren.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


def setup_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session


def fetch_page_content(url, session, timeout=30):
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        if not response.text.strip():
            logging.warning(f"Пустой ответ от {url}")
            return None
        logging.info(f"Успешно загружено: {url}")
        return response.text
    except requests.RequestException as e:
        logging.error(f"Ошибка при загрузке {url}: {e}")
        return None


def parse_diseases(url, session):
    html_content = fetch_page_content(url, session)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    diseases = []

    for section in soup.find_all(['div', 'section'], class_=re.compile('disease|item|content', re.I)):
        title = section.find(['h2', 'h3', 'span'], class_=re.compile('title|name', re.I))
        description = section.find(['p', 'div'], class_=re.compile('description|text', re.I))
        link = section.find('a', href=True)

        if title and description:
            disease = {
                'name': title.get_text(strip=True),
                'description': description.get_text(strip=True),
                'detail_url': link['href'] if link else url
            }
            diseases.append(disease)
            logging.info(f"Извлечена болезнь: {disease['name']}")

    return diseases


def parse_pests(url, session):
    html_content = fetch_page_content(url, session)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    pests = []

    for section in soup.find_all(['div', 'section'], class_=re.compile('pest|item|content', re.I)):
        title = section.find(['h2', 'h3', 'span'], class_=re.compile('title|name', re.I))
        description = section.find(['p', 'div'], class_=re.compile('description|text', re.I))
        link = section.find('a', href=True)

        if title and description:
            pest = {
                'name': title.get_text(strip=True),
                'description': description.get_text(strip=True),
                'detail_url': link['href'] if link else url
            }
            pests.append(pest)
            logging.info(f"Извлечен вредитель: {pest['name']}")

    return pests


def parse_weeds(url, session):
    html_content = fetch_page_content(url, session)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    weeds = []

    for section in soup.find_all(['div', 'section'], class_=re.compile('weed|item|content', re.I)):
        title = section.find(['h2', 'h3', 'span'], class_=re.compile('title|name', re.I))
        scientific_name = section.find(['p', 'span'], class_=re.compile('scientific|latin', re.I))
        link = section.find('a', href=True)

        if title:
            weed = {
                'name': title.get_text(strip=True),
                'scientific_name': scientific_name.get_text(strip=True) if scientific_name else '',
                'detail_url': link['href'] if link else url
            }
            weeds.append(weed)
            logging.info(f"Извлечен сорняк: {weed['name']}")

    return weeds


def main():
    base_url = 'https://betaren.ru'
    urls = {
        'diseases': {
            'cereals': f'{base_url}/harmful/bolezni/bolezni-zernovykh-kultur/',
            'rapeseed': f'{base_url}/harmful/bolezni/bolezni-rapsa/',
            'corn': f'{base_url}/harmful/bolezni/bolezni-kukuruzy/'
        },
        'pests': {
            'cereals': f'{base_url}/harmful/vrediteli/vrediteli-zernovykh-kultur/',
            'rapeseed': f'{base_url}/harmful/vrediteli/vrediteli-rapsa/',
            'corn': f'{base_url}/harmful/vrediteli/vrediteli-kukuruzy/'
        },
        'weeds': f'{base_url}/harmful/sornyaki/'
    }

    session = setup_session()
    data = {
        'diseases': {
            'cereals': parse_diseases(urls['diseases']['cereals'], session),
            'rapeseed': parse_diseases(urls['diseases']['rapeseed'], session),
            'corn': parse_diseases(urls['diseases']['corn'], session)
        },
        'pests': {
            'cereals': parse_pests(urls['pests']['cereals'], session),
            'rapeseed': parse_pests(urls['pests']['rapeseed'], session),
            'corn': parse_pests(urls['pests']['corn'], session)
        },
        'weeds': parse_weeds(urls['weeds'], session)
    }

    with open('betaren_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    logging.info("Данные успешно сохранены в betaren_data.json")
    print("Данные успешно сохранены в betaren_data.json. Подробности в scrape_betaren.log")


if __name__ == "__main__":
    main()