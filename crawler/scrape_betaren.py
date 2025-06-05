#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import json
import re
import random
import time
from urllib.parse import urljoin
import os
import csv
import uuid
import logging
from dotenv import load_dotenv
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from twocaptcha import TwoCaptcha

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("betaren_scrape.log", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BetarenScraper")

# Загрузка настроек из .env
load_dotenv()

# Настройки
SLEEP_RANGE = (5.0, 10.0)
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 5))
OUTPUT_DIR = os.getenv('DOWNLOAD_DIR', 'downloads')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
TWOCAPTCHA_API_KEY = os.getenv('TWOCAPTCHA_API_KEY', '')
PROXY_LIST = os.getenv('PROXY_LIST', '').split(',') if os.getenv('PROXY_LIST') else []
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', 'D:/crawler_risks/chromedriver.exe')

# Проверка ключей API
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY не задан. Переводы не будут выполняться.")
else:
    logger.info("OPENAI_API_KEY настроен успешно.")

if not TWOCAPTCHA_API_KEY:
    logger.warning("TWOCAPTCHA_API_KEY не задан. Обход капчи невозможен.")
else:
    logger.info("TWOCAPTCHA_API_KEY настроен успешно.")

# Инициализация OpenAI
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Список User-Agent
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

# GUID культур
crop_guids = {
    "пшеница": "501933b1-b43d-11e9-a3c5-00155d012200",
    "ячмень": "ed8d52db-9b99-4ac3-9691-082829953c46",
    "кукуруза": "c61ecabe-229e-4361-921a-081125d5c3c1",
    "овес": "c593d0c4-653c-418b-9ac4-35d58f3ff627",
    "рапс": "f503750b-f20d-4bf7-af68-ce922974018c",
    "горчица": "4f091a7c-30f4-4825-a76a-1ffffb89483b",
    "соя": "soy_guid_placeholder",
    "сахарная свекла": "sugar_beet_guid_placeholder",
    "подсолнечник": "sunflower_guid_placeholder",
    "горох": "pea_guid_placeholder",
    "нут": "nut_guid_placeholder",
    "лен": "flax_guid_placeholder",
    "картофель": "potato_guid_placeholder",
    "садовые культуры": "orchard_guid_placeholder",
    "виноградники": "vineyard_guid_placeholder"
}

# Создание директорий
os.makedirs(OUTPUT_DIR, exist_ok=True)
for folder in ["diseases", "pests", "weeds"]:
    os.makedirs(os.path.join(OUTPUT_DIR, "images", folder), exist_ok=True)

def translate_text(text, target_lang):
    if not text or not client:
        return ''
    try:
        max_length = 1000
        if len(text) > max_length:
            parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            translated_parts = []
            for part in parts:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ты профессиональный переводчик, специализирующийся на сельскохозяйственной терминологии."},
                        {"role": "user", "content": f"Переведи следующий текст с русского на {target_lang}, сохраняя агрономическую терминологию:\n\n{part}"}
                    ],
                    max_tokens=2000,
                    temperature=0.2
                )
                translated_parts.append(response.choices[0].message.content.strip())
            return ' '.join(translated_parts)
        else:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты профессиональный переводчик, специализирующийся на сельскохозяйственной терминологии."},
                    {"role": "user", "content": f"Переведи следующий текст с русского на {target_lang}, сохраняя агрономическую терминологию:\n\n{text}"}
                ],
                max_tokens=2000,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка перевода текста: {e}")
        return ''

def solve_recaptcha(site_key, url):
    """Решает reCAPTCHA с использованием 2Captcha."""
    if not TWOCAPTCHA_API_KEY:
        logger.warning("TWOCAPTCHA_API_KEY не задан, пропускаем решение капчи.")
        return None

    solver = TwoCaptcha(TWOCAPTCHA_API_KEY)
    try:
        result = solver.recaptcha(sitekey=site_key, url=url)
        logger.info(f"reCAPTCHA решена: {result['code']}")
        return result['code']
    except Exception as e:
        logger.error(f"Ошибка при решении reCAPTCHA: {e}")
        return None

def fetch_page_content(url):
    options = webdriver.ChromeOptions()
    user_agent = random.choice(USER_AGENTS)  # Исправление: выбор случайного User-Agent
    options.add_argument(f'user-agent={user_agent}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-geolocation')

    if PROXY_LIST:
        proxy = random.choice([p for p in PROXY_LIST if p])
        logger.debug(f"Используется прокси: {proxy}")
        options.add_argument(f'--proxy-server={proxy}')

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(random.uniform(5.0, 10.0))

        # Проверка reCAPTCHA
        if 'g-recaptcha' in driver.page_source:
            logger.debug("Обнаружена reCAPTCHA, пытаемся решить...")
            try:
                site_key = driver.find_element(By.CLASS_NAME, 'g-recaptcha').get_attribute('data-sitekey')
                captcha_response = solve_recaptcha(site_key, url)
                if captcha_response:
                    driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{captcha_response}";')
                    driver.find_element(By.ID, 'feedback-form').submit()
                    time.sleep(random.uniform(5.0, 10.0))
                    logger.debug("reCAPTCHA решена")
                else:
                    logger.warning("Не удалось решить reCAPTCHA")
            except Exception as e:
                logger.error(f"Ошибка при решении reCAPTCHA: {e}")

        html_content = driver.page_source
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.debug(f"HTML сохранен в debug_page.html для {url}")
        return html_content
    except Exception as e:
        logger.error(f"Ошибка при загрузке страницы {url}: {e}")
        return None
    finally:
        driver.quit()

def download_image(url, folder, filename, referer):
    if not url:
        logger.debug("URL изображения отсутствует")
        return ''

    try:
        os.makedirs(f'{OUTPUT_DIR}/{folder}', exist_ok=True)
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': referer
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        image_path = os.path.join(OUTPUT_DIR, folder, filename)
        with open(image_path, 'wb') as f:
            f.write(response.content)
        logger.debug(f"Изображение сохранено: {image_path}")
        return image_path
    except Exception as e:
        logger.error(f"Ошибка при скачивании изображения {url}: {e}")
        return ''

def parse_diseases(url, crop):
    """Парсит данные о болезнях с общей и детальных страниц."""
    html_content = fetch_page_content(url)
    if not html_content:
        logger.debug(f"Не удалось загрузить контент для {url}")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    diseases = []
    
    # Проверка, является ли страница общей (списком болезней)
    is_list_page = bool(soup.find('div', class_='harmful-list'))
    
    if is_list_page:
        # Сбор ссылок на детальные страницы
        sections = soup.find_all('div', class_='harmful-list__item')
        detail_urls = []
        for section in sections:
            link_elem = section.find('a', class_='harmful-list__title', href=True)
            if link_elem and '/harmful/bolezni/' in link_elem['href'] and link_elem['href'] != url:
                detail_url = urljoin(url, link_elem['href'])
                if detail_url not in detail_urls:
                    detail_urls.append(detail_url)
        logger.debug(f"Найдено {len(detail_urls)} детальных страниц болезней для {url}: {detail_urls}")
    else:
        # Если это детальная страница, добавляем её напрямую
        detail_urls = [url]

    # Парсинг детальных страниц
    for detail_url in detail_urls:
        detail_html = fetch_page_content(detail_url)
        if not detail_html:
            logger.debug(f"Не удалось загрузить детальную страницу {detail_url}")
            continue

        detail_soup = BeautifulSoup(detail_html, 'html.parser')
        
        # Обновленные селекторы
        title_elem = detail_soup.find('h1') or detail_soup.find(['h2'], class_=re.compile('harmful__title|title|name|heading'))
        description_elem = detail_soup.find('div', class_=re.compile('harmful__content|content|description|info|summary|body')) or detail_soup.find('p')
        symptoms_elem = detail_soup.find('div', class_=re.compile('symptoms|signs|damage')) or detail_soup.find('p', string=re.compile('симптомы|признаки|проявления|поражение|характеристика', re.I))
        conditions_elem = detail_soup.find('div', class_=re.compile('conditions|development|environment')) or detail_soup.find('p', string=re.compile('условия|развитие|факторы|распространение', re.I))
        measures_elem = detail_soup.find('div', class_=re.compile('control|measures|protection')) or detail_soup.find('p', string=re.compile('меры|борьба|защита|контроль|рекомендации', re.I))
        image_elem = detail_soup.find('img', class_=re.compile('gallery__img|harmful__image|image|photo')) or detail_soup.find('img', src=True)

        logger.debug(f"Детальная страница {detail_url}: Заголовок={title_elem is not None}, Описание={description_elem is not None}, Симптомы={symptoms_elem is not None}, Условия={conditions_elem is not None}, Меры={measures_elem is not None}, Изображение={image_elem is not None}")

        if title_elem:
            name = title_elem.get_text(strip=True)
            description = description_elem.get_text(strip=True) if description_elem else ''
            symptoms = symptoms_elem.get_text(strip=True) if symptoms_elem else description
            conditions = conditions_elem.get_text(strip=True) if conditions_elem else ''
            measures = measures_elem.get_text(strip=True) if measures_elem else ''
            image_url = urljoin(detail_url, image_elem['src']) if image_elem and 'company-logo' not in image_elem['src'] else None

            # Пропустить некорректные заголовки
            if name.lower() in ['не пропустите', 'подписка', 'обратная связь']:
                logger.debug(f"Пропущен некорректный заголовок: {name}")
                continue

            # Отладка содержимого
            logger.debug(f"Извлеченные данные: Название={name}, Описание={description[:100]}..., Симптомы={symptoms[:100]}..., Условия={conditions[:100]}..., Меры={measures[:100]}..., Изображение={image_url}")

            # Упрощенная проверка данных
            if not description.strip() and not symptoms.strip():
                logger.debug(f"Пропущена запись для {name}: отсутствует описание и симптомы")
                continue

            disease_id = str(uuid.uuid4())
            image_filename = f"disease_{name.replace(' ', '_').replace('/', '_')}_{disease_id}.jpg"
            image_path = download_image(image_url, 'diseases', image_filename, detail_url) if image_url else ''

            diseases.append({
                'id': disease_id,
                'name': name,
                'name_en': translate_text(name, 'en') if name else '',
                'scientific_name': '',
                'is_active': True,
                'description_ru': description,
                'description_ua': translate_text(description, 'ua') if description else '',
                'description_en': translate_text(description, 'en') if description else '',
                'symptoms_ru': symptoms,
                'symptoms_ua': translate_text(symptoms, 'ua') if symptoms else '',
                'symptoms_en': translate_text(symptoms, 'en') if symptoms else '',
                'development_conditions_ru': conditions,
                'development_conditions_ua': translate_text(conditions, 'ua') if conditions else '',
                'development_conditions_en': translate_text(conditions, 'en') if conditions else '',
                'control_measures_ru': measures,
                'control_measures_ua': translate_text(measures, 'ua') if measures else '',
                'control_measures_en': translate_text(measures, 'en') if measures else '',
                'photo_path': image_path,
                'source_urls': detail_url,
                'crops': crop
            })
            logger.info(f"Добавлена болезнь: {name} для {crop}")

            # Сохранить HTML для отладки
            with open(f'debug_disease_{disease_id}.html', 'w', encoding='utf-8') as f:
                f.write(detail_soup.prettify())
            logger.debug(f"HTML детальной страницы сохранен в debug_disease_{disease_id}.html")

    logger.debug(f"Итоговый список болезней: {len(diseases)} записей")
    return diseases

def parse_pests(url, crop):
    """Парсит данные о вредителях с общей и детальных страниц."""
    html_content = fetch_page_content(url)
    if not html_content:
        logger.debug(f"Не удалось загрузить контент для {url}")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    pests = []
    
    sections = soup.find_all(['div', 'section', 'article', 'li', 'a'], class_=re.compile('harmful|pest|item|block|entry|list|link|card'))
    detail_urls = []
    for section in sections:
        link_elem = section.find('a', href=True)
        if link_elem and '/harmful/vrediteli/' in link_elem['href'] and link_elem['href'] != url:
            detail_url = urljoin(url, link_elem['href'])
            if detail_url not in detail_urls:
                detail_urls.append(detail_url)
    
    logger.debug(f"Найдено {len(detail_urls)} детальных страниц вредителей для {url}: {detail_urls}")

    for detail_url in detail_urls:
        detail_html = fetch_page_content(detail_url)
        if not detail_html:
            logger.debug(f"Не удалось загрузить детальную страницу {detail_url}")
            continue

        detail_soup = BeautifulSoup(detail_html, 'html.parser')
        
        title_elem = detail_soup.find(['h1', 'h2'], class_=re.compile('harmful__title|title|name|heading')) or detail_soup.find(['h1', 'h2'])
        description_elem = detail_soup.find(['div', 'p'], class_=re.compile('harmful__content|content|description|info|summary|body')) or detail_soup.find('p')
        damage_elem = detail_soup.find(['div', 'p'], class_=re.compile('damage|symptoms|impact')) or detail_soup.find('p', string=re.compile('ущерб|повреждения', re.I))
        biology_elem = detail_soup.find(['div', 'p'], class_=re.compile('biology|life_cycle|development')) or detail_soup.find('p', string=re.compile('биология|жизненный цикл', re.I))
        measures_elem = detail_soup.find(['div', 'p'], class_=re.compile('control|measures|protection')) or detail_soup.find('p', string=re.compile('меры|борьба|защита', re.I))
        image_elem = detail_soup.find('img', class_=re.compile('harmful__image|image|photo')) or detail_soup.find('img', src=True)

        logger.debug(f"Детальная страница {detail_url}: Заголовок={title_elem is not None}, Описание={description_elem is not None}, Ущерб={damage_elem is not None}, Биология={biology_elem is not None}, Меры={measures_elem is not None}, Изображение={image_elem is not None}")

        if title_elem:
            name = title_elem.get_text(strip=True)
            description = description_elem.get_text(strip=True) if description_elem else ''
            damage = damage_elem.get_text(strip=True) if damage_elem else description
            biology = biology_elem.get_text(strip=True) if biology_elem else ''
            measures = measures_elem.get_text(strip=True) if measures_elem else ''
            image_url = urljoin(detail_url, image_elem['src']) if image_elem and 'company-logo' not in image_elem['src'] else None

            if name.lower() in ['не пропустите', 'подписка', 'обратная связь']:
                logger.debug(f"Пропущен некорректный заголовок: {name}")
                continue

            pest_id = str(uuid.uuid4())
            image_filename = f"pest_{name.replace(' ', '_').replace('/', '_')}_{pest_id}.jpg"
            image_path = download_image(image_url, 'pests', image_filename, detail_url) if image_url else ''

            pests.append({
                'id': pest_id,
                'name': name,
                'name_en': translate_text(name, 'en') if name else '',
                'scientific_name': '',
                'is_active': True,
                'description_ru': description,
                'description_ua': translate_text(description, 'ua') if description else '',
                'description_en': translate_text(description, 'en') if description else '',
                'damage_symptoms_ru': damage,
                'damage_symptoms_ua': translate_text(damage, 'ua') if damage else '',
                'damage_symptoms_en': translate_text(damage, 'en') if damage else '',
                'biology_ru': biology,
                'biology_ua': translate_text(biology, 'ua') if biology else '',
                'biology_en': translate_text(biology, 'en') if biology else '',
                'control_measures_ru': measures,
                'control_measures_ua': translate_text(measures, 'ua') if measures else '',
                'control_measures_en': translate_text(measures, 'en') if measures else '',
                'photo_path': image_path,
                'source_urls': detail_url,
                'crops': crop
            })
            logger.info(f"Добавлен вредитель: {name} для {crop}")

            with open(f'debug_pest_{pest_id}.html', 'w', encoding='utf-8') as f:
                f.write(detail_soup.prettify())
            logger.debug(f"HTML детальной страницы сохранен в debug_pest_{pest_id}.html")

    logger.debug(f"Итоговый список вредителей: {len(pests)} записей")
    return pests

def parse_weeds(url):
    """Парсит данные о сорняках с общей и детальных страниц."""
    html_content = fetch_page_content(url)
    if not html_content:
        logger.debug(f"Не удалось загрузить контент для {url}")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    weeds = []
    
    sections = soup.find_all(['div', 'section', 'article', 'li', 'a'], class_=re.compile('harmful|weed|item|block|entry|list|link|card'))
    detail_urls = []
    for section in sections:
        link_elem = section.find('a', href=True)
        if link_elem and '/harmful/sornyaki/' in link_elem['href'] and link_elem['href'] != url:
            detail_url = urljoin(url, link_elem['href'])
            if detail_url not in detail_urls:
                detail_urls.append(detail_url)
    
    logger.debug(f"Найдено {len(detail_urls)} детальных страниц сорняков для {url}: {detail_urls}")

    for detail_url in detail_urls:
        detail_html = fetch_page_content(detail_url)
        if not detail_html:
            logger.debug(f"Не удалось загрузить детальную страницу {detail_url}")
            continue

        detail_soup = BeautifulSoup(detail_html, 'html.parser')
        
        title_elem = detail_soup.find(['h1', 'h2'], class_=re.compile('harmful__title|title|name|heading')) or detail_soup.find(['h1', 'h2'])
        scientific_elem = detail_soup.find(['p', 'span', 'i'], class_=re.compile('scientific|latin|name')) or detail_soup.find('i')
        description_elem = detail_soup.find(['div', 'p'], class_=re.compile('harmful__content|content|description|info|summary|body')) or detail_soup.find('p')
        features_elem = detail_soup.find(['div', 'p'], class_=re.compile('features|biology|characteristics')) or detail_soup.find('p', string=re.compile('биология|характеристики', re.I))
        harmfulness_elem = detail_soup.find(['div', 'p'], class_=re.compile('harmfulness|damage|impact')) or detail_soup.find('p', string=re.compile('вредоносность|ущерб', re.I))
        measures_elem = detail_soup.find(['div', 'p'], class_=re.compile('control|measures|protection')) or detail_soup.find('p', string=re.compile('меры|борьба|защита', re.I))
        image_elem = detail_soup.find('img', class_=re.compile('harmful__image|image|photo')) or detail_soup.find('img', src=True)

        logger.debug(f"Детальная страница {detail_url}: Заголовок={title_elem is not None}, Научное имя={scientific_elem is not None}, Описание={description_elem is not None}, Биология={features_elem is not None}, Вредоносность={harmfulness_elem is not None}, Меры={measures_elem is not None}, Изображение={image_elem is not None}")

        if title_elem:
            name = title_elem.get_text(strip=True)
            scientific_name = scientific_elem.get_text(strip=True) if scientific_elem else ''
            description = description_elem.get_text(strip=True) if description_elem else ''
            features = features_elem.get_text(strip=True) if features_elem else description
            harmfulness = harmfulness_elem.get_text(strip=True) if harmfulness_elem else ''
            measures = measures_elem.get_text(strip=True) if measures_elem else ''
            image_url = urljoin(detail_url, image_elem['src']) if image_elem and 'company-logo' not in image_elem['src'] else None

            if name.lower() in ['не пропустите', 'подписка', 'обратная связь']:
                logger.debug(f"Пропущен некорректный заголовок: {name}")
                continue

            weed_id = str(uuid.uuid4())
            image_filename = f"weed_{name.replace(' ', '_').replace('/', '_')}_{weed_id}.jpg"
            image_path = download_image(image_url, 'weeds', image_filename, detail_url) if image_url else ''

            weeds.append({
                'id': weed_id,
                'name': name,
                'name_en': translate_text(name, 'en') if name else '',
                'scientific_name': scientific_name,
                'is_active': True,
                'description_ru': description,
                'description_ua': translate_text(description, 'ua') if description else '',
                'description_en': translate_text(description, 'en') if description else '',
                'biological_features_ru': features,
                'biological_features_ua': translate_text(features, 'ua') if features else '',
                'biological_features_en': translate_text(features, 'en') if features else '',
                'harmfulness_ru': harmfulness,
                'harmfulness_ua': translate_text(harmfulness, 'ua') if harmfulness else '',
                'harmfulness_en': translate_text(harmfulness, 'en') if harmfulness else '',
                'control_measures_ru': measures,
                'control_measures_ua': translate_text(measures, 'ua') if measures else '',
                'control_measures_en': translate_text(measures, 'en') if measures else '',
                'photo_path': image_path,
                'source_urls': detail_url
            })
            logger.info(f"Добавлен сорняк: {name}")

            with open(f'debug_weed_{weed_id}.html', 'w', encoding='utf-8') as f:
                f.write(detail_soup.prettify())
            logger.debug(f"HTML детальной страницы сохранен в debug_weed_{weed_id}.html")

    logger.debug(f"Итоговый список сорняков: {len(weeds)} записей")
    return weeds

def save_to_csv(data, filename, fieldnames):
    """Сохраняет данные в CSV."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({k: str(v) for k, v in row.items() if k in fieldnames})
        logger.info(f"Сохранено {len(data)} записей в {filename}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении CSV {filename}: {e}")

def main():
    base_url = 'https://betaren.ru'
    urls = {
        'diseases': {
            'cereals': f'{base_url}/harmful/bolezni/bolezni-zernovykh-kultur/',
            'rapeseed': f'{base_url}/harmful/bolezni/bolezni-rapsa/',
            'corn': f'{base_url}/harmful/bolezni/bolezni-kukuruzy/',
            'soy': f'{base_url}/harmful/bolezni/bolezni-soi/',
            'sugar_beet': f'{base_url}/harmful/bolezni/bolezni-sakharnoy-svekly/',
            'sunflower': f'{base_url}/harmful/bolezni/bolezni-podsolnechnika/',
            'pea_nut': f'{base_url}/harmful/bolezni/bolezni-gorokha-i-nuta/',
            'flax': f'{base_url}/harmful/bolezni/bolezni-lna/',
            'potato': f'{base_url}/harmful/bolezni/bolezni-kartofelya/',
            'orchard': f'{base_url}/harmful/bolezni/bolezni-sadovykh-kultur/',
            'vineyard': f'{base_url}/harmful/bolezni/bolezni-vinogradnikov/'
        },
        'pests': {
            'cereals': f'{base_url}/harmful/vrediteli/vrediteli-zernovykh-kultur/',
            'rapeseed': f'{base_url}/harmful/vrediteli/vrediteli-rapsa/',
            'corn': f'{base_url}/harmful/vrediteli/vrediteli-kukuruzy/',
            'soy': f'{base_url}/harmful/vrediteli/vrediteli-soi/',
            'sugar_beet': f'{base_url}/harmful/vrediteli/vrediteli-sakharnoy-svekly/',
            'sunflower': f'{base_url}/harmful/vrediteli/vrediteli-podsolnechnika/',
            'pea_nut': f'{base_url}/harmful/vrediteli/vrediteli-gorokha-i-nuta/',
            'flax': f'{base_url}/harmful/vrediteli/vrediteli-lna/',
            'potato': f'{base_url}/harmful/vrediteli/vrediteli-kartofelya/',
            'orchard': f'{base_url}/harmful/vrediteli/vrediteli-sadovykh-kultur/',
            'vineyard': f'{base_url}/harmful/vrediteli/vrediteli-vinogradnikov/'
        },
        'weeds': f'{base_url}/harmful/sornyaki/'
    }

    # Инициализация списков для данных
    diseases = []
    disease_descriptions = []
    disease_crops = []
    disease_images = []
    pests = []
    pest_descriptions = []
    pest_crops = []
    pest_images = []
    weeds = []
    weed_descriptions = []
    weed_crops = []
    weed_images = []

    # Соответствие категорий и культур
    crop_mapping = {
        'cereals': ['пшеница', 'ячмень', 'овес'],
        'rapeseed': ['рапс'],
        'corn': ['кукуруза'],
        'soy': ['соя'],
        'sugar_beet': ['сахарная свекла'],
        'sunflower': ['подсолнечник'],
        'pea_nut': ['горох', 'нут'],
        'flax': ['лен'],
        'potato': ['картофель'],
        'orchard': ['садовые культуры'],
        'vineyard': ['виноградники']
    }

    # Парсинг болезней
    for category, crop_url in urls['diseases'].items():
        for crop_name in crop_mapping[category]:
            logger.info(f"Парсинг болезней для культуры: {crop_name}")
            try:
                crop_diseases = parse_diseases(crop_url, crop_name)
                logger.debug(f"Извлечено {len(crop_diseases)} болезней для {crop_name}: {[d['name'] for d in crop_diseases]}")
                
                for disease in crop_diseases:
                    disease_id = disease['id']
                    desc_id = str(uuid.uuid4())
                    img_id = str(uuid.uuid4())

                    diseases.append({
                        'id': disease_id,
                        'name': disease['name'],
                        'name_en': disease['name_en'],
                        'scientific_name': disease['scientific_name'],
                        'is_active': disease['is_active']
                    })

                    disease_descriptions.append({
                        'id': desc_id,
                        'disease_id': disease_id,
                        'description_ru': disease['description_ru'],
                        'description_ua': disease['description_ua'],
                        'description_en': disease['description_en'],
                        'symptoms_ru': disease['symptoms_ru'],
                        'symptoms_ua': disease['symptoms_ua'],
                        'symptoms_en': disease['symptoms_en'],
                        'development_conditions_ru': disease['development_conditions_ru'],
                        'development_conditions_ua': disease['development_conditions_ua'],
                        'development_conditions_en': disease['development_conditions_en'],
                        'control_measures_ru': disease['control_measures_ru'],
                        'control_measures_ua': disease['control_measures_ua'],
                        'control_measures_en': disease['control_measures_en'],
                        'photo_path': disease['photo_path'],
                        'source_urls': disease['source_urls'],
                        'version': 1
                    })

                    disease_crops.append({
                        'disease_id': disease_id,
                        'crops': crop_name
                    })

                    if disease['photo_path']:
                        disease_images.append({
                            'id': img_id,
                            'disease_id': disease_id,
                            'image_url': disease['source_urls'],
                            'image_path': disease['photo_path'],
                            'version': 1
                        })
            except Exception as e:
                logger.error(f"Ошибка при парсинге болезней для {crop_name}: {e}")

    # Парсинг вредителей
    for category, crop_url in urls['pests'].items():
        for crop_name in crop_mapping[category]:
            logger.info(f"Парсинг вредителей для культуры: {crop_name}")
            try:
                crop_pests = parse_pests(crop_url, crop_name)
                logger.debug(f"Извлечено {len(crop_pests)} вредителей для {crop_name}: {[p['name'] for p in crop_pests]}")
                
                for pest in crop_pests:
                    pest_id = pest['id']
                    desc_id = str(uuid.uuid4())
                    img_id = str(uuid.uuid4())

                    pests.append({
                        'id': pest_id,
                        'name': pest['name'],
                        'name_en': pest['name_en'],
                        'scientific_name': pest['scientific_name'],
                        'is_active': pest['is_active']
                    })

                    pest_descriptions.append({
                        'id': desc_id,
                        'vermin_id': pest_id,
                        'description_ru': pest['description_ru'],
                        'description_ua': pest['description_ua'],
                        'description_en': pest['description_en'],
                        'damage_symptoms_ru': pest['damage_symptoms_ru'],
                        'damage_symptoms_ua': pest['damage_symptoms_ua'],
                        'damage_symptoms_en': pest['damage_symptoms_en'],
                        'biology_ru': pest['biology_ru'],
                        'biology_ua': pest['biology_ua'],
                        'biology_en': pest['biology_en'],
                        'control_measures_ru': pest['control_measures_ru'],
                        'control_measures_ua': pest['control_measures_ua'],
                        'control_measures_en': pest['control_measures_en'],
                        'photo_path': pest['photo_path'],
                        'source_urls': pest['source_urls'],
                        'version': 1
                    })

                    pest_crops.append({
                        'vermin_id': pest_id,
                        'crops': crop_name
                    })

                    if pest['photo_path']:
                        pest_images.append({
                            'id': img_id,
                            'vermin_id': pest_id,
                            'image_url': pest['source_urls'],
                            'image_path': pest['photo_path'],
                            'version': 1
                        })
            except Exception as e:
                logger.error(f"Ошибка при парсинге вредителей для {crop_name}: {e}")

    # Парсинг сорняков
    logger.info("Парсинг сорняков")
    try:
        crop_weeds = parse_weeds(urls['weeds'])
        logger.debug(f"Извлечено {len(crop_weeds)} сорняков: {[w['name'] for w in crop_weeds]}")
        
        for weed in crop_weeds:
            weed_id = weed['id']
            desc_id = str(uuid.uuid4())
            img_id = str(uuid.uuid4())

            weeds.append({
                'id': weed_id,
                'name': weed['name'],
                'name_en': weed['name_en'],
                'scientific_name': weed['scientific_name'],
                'is_active': weed['is_active']
            })

            weed_descriptions.append({
                'id': desc_id,
                'weed_id': weed_id,
                'description_ru': weed['description_ru'],
                'description_ua': weed['description_ua'],
                'description_en': weed['description_en'],
                'biological_features_ru': weed['biological_features_ru'],
                'biological_features_ua': weed['biological_features_ua'],
                'biological_features_en': weed['biological_features_en'],
                'harmfulness_ru': weed['harmfulness_ru'],
                'harmfulness_ua': weed['harmfulness_ua'],
                'harmfulness_en': weed['harmfulness_en'],
                'control_measures_ru': weed['control_measures_ru'],
                'control_measures_ua': weed['control_measures_ua'],
                'control_measures_en': weed['control_measures_en'],
                'photo_path': weed['photo_path'],
                'source_urls': weed['source_urls'],
                'version': 1
            })

            for crop in ['пшеница', 'ячмень', 'кукуруза', 'овес', 'рапс', 'горчица', 'соя', 'сахарная свекла', 'подсолнечник', 'горох', 'нут', 'лен', 'картофель']:
                weed_crops.append({
                    'weed_id': weed_id,
                    'crops': crop
                })

            if weed['photo_path']:
                weed_images.append({
                    'id': img_id,
                    'weed_id': weed_id,
                    'image_url': weed['source_urls'],
                    'image_path': weed['photo_path'],
                    'version': 1
                })
    except Exception as e:
        logger.error(f"Ошибка при парсинге сорняков: {e}")

    # Отладочный вывод перед сохранением
    logger.debug(f"Общее количество болезней: {len(diseases)}")
    logger.debug(f"Общее количество описаний болезней: {len(disease_descriptions)}")
    logger.debug(f"Общее количество культур для болезней: {len(disease_crops)}")
    logger.debug(f"Общее количество изображений болезней: {len(disease_images)}")
    logger.debug(f"Общее количество вредителей: {len(pests)}")
    logger.debug(f"Общее количество описаний вредителей: {len(pest_descriptions)}")
    logger.debug(f"Общее количество культур для вредителей: {len(pest_crops)}")
    logger.debug(f"Общее количество изображений вредителей: {len(pest_images)}")
    logger.debug(f"Общее количество сорняков: {len(weeds)}")
    logger.debug(f"Общее количество описаний сорняков: {len(weed_descriptions)}")
    logger.debug(f"Общее количество культур для сорняков: {len(weed_crops)}")
    logger.debug(f"Общее количество изображений сорняков: {len(weed_images)}")

    # Сохранение данных в CSV
    try:
        save_to_csv(diseases, os.path.join(OUTPUT_DIR, 'diseases.csv'),
                    ['id', 'name', 'name_en', 'scientific_name', 'is_active'])
        save_to_csv(disease_descriptions, os.path.join(OUTPUT_DIR, 'disease_descriptions.csv'),
                    ['id', 'disease_id', 'description_ru', 'description_ua', 'description_en',
                     'symptoms_ru', 'symptoms_ua', 'symptoms_en',
                     'development_conditions_ru', 'development_conditions_ua', 'development_conditions_en',
                     'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                     'photo_path', 'source_urls', 'version'])
        save_to_csv(disease_crops, os.path.join(OUTPUT_DIR, 'disease_crops.csv'),
                    ['disease_id', 'crops'])
        save_to_csv(disease_images, os.path.join(OUTPUT_DIR, 'disease_images.csv'),
                    ['id', 'disease_id', 'image_url', 'image_path', 'version'])

        save_to_csv(pests, os.path.join(OUTPUT_DIR, 'vermins.csv'),
                    ['id', 'name', 'name_en', 'scientific_name', 'is_active'])
        save_to_csv(pest_descriptions, os.path.join(OUTPUT_DIR, 'vermin_descriptions.csv'),
                    ['id', 'vermin_id', 'description_ru', 'description_ua', 'description_en',
                     'damage_symptoms_ru', 'damage_symptoms_ua', 'damage_symptoms_en',
                     'biology_ru', 'biology_ua', 'biology_en',
                     'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                     'photo_path', 'source_urls', 'version'])
        save_to_csv(pest_crops, os.path.join(OUTPUT_DIR, 'vermin_crops.csv'),
                    ['vermin_id', 'crops'])
        save_to_csv(pest_images, os.path.join(OUTPUT_DIR, 'vermin_images.csv'),
                    ['id', 'vermin_id', 'image_url', 'image_path', 'version'])

        save_to_csv(weeds, os.path.join(OUTPUT_DIR, 'weeds.csv'),
                    ['id', 'name', 'name_en', 'scientific_name', 'is_active'])
        save_to_csv(weed_descriptions, os.path.join(OUTPUT_DIR, 'weed_descriptions.csv'),
                    ['id', 'weed_id', 'description_ru', 'description_ua', 'description_en',
                     'biological_features_ru', 'biological_features_ua', 'biological_features_en',
                     'harmfulness_ru', 'harmfulness_ua', 'harmfulness_en',
                     'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                     'photo_path', 'source_urls', 'version'])
        save_to_csv(weed_crops, os.path.join(OUTPUT_DIR, 'weed_crops.csv'),
                    ['weed_id', 'crops'])
        save_to_csv(weed_images, os.path.join(OUTPUT_DIR, 'weed_images.csv'),
                    ['id', 'weed_id', 'image_url', 'image_path', 'version'])
    except Exception as e:
        logger.error(f"Ошибка при сохранении CSV-файлов: {e}")

    # Создание JSON-отчета
    try:
        data = {
            'diseases': {
                'cereals': [d for d in diseases if any(c['crops'] in ['пшеница', 'ячмень', 'овес'] for c in disease_crops if c['disease_id'] == d['id'])],
                'rapeseed': [d for d in diseases if any(c['crops'] == 'рапс' for c in disease_crops if c['disease_id'] == d['id'])],
                'corn': [d for d in diseases if any(c['crops'] == 'кукуруза' for c in disease_crops if c['disease_id'] == d['id'])],
                'soy': [d for d in diseases if any(c['crops'] == 'соя' for c in disease_crops if c['disease_id'] == d['id'])],
                'sugar_beet': [d for d in diseases if any(c['crops'] == 'сахарная свекла' for c in disease_crops if c['disease_id'] == d['id'])],
                'sunflower': [d for d in diseases if any(c['crops'] == 'подсолнечник' for c in disease_crops if c['disease_id'] == d['id'])],
                'pea_nut': [d for d in diseases if any(c['crops'] in ['горох', 'нут'] for c in disease_crops if c['disease_id'] == d['id'])],
                'flax': [d for d in diseases if any(c['crops'] == 'лен' for c in disease_crops if c['disease_id'] == d['id'])],
                'potato': [d for d in diseases if any(c['crops'] == 'картофель' for c in disease_crops if c['disease_id'] == d['id'])],
                'orchard': [d for d in diseases if any(c['crops'] == 'садовые культуры' for c in disease_crops if c['disease_id'] == d['id'])],
                'vineyard': [d for d in diseases if any(c['crops'] == 'виноградники' for c in disease_crops if c['disease_id'] == d['id'])]
            },
            'pests': {
                'cereals': [p for p in pests if any(c['crops'] in ['пшеница', 'ячмень', 'овес'] for c in pest_crops if c['vermin_id'] == p['id'])],
                'rapeseed': [p for p in pests if any(c['crops'] == 'рапс' for c in pest_crops if c['vermin_id'] == p['id'])],
                'corn': [p for p in pests if any(c['crops'] == 'кукуруза' for c in pest_crops if c['vermin_id'] == p['id'])],
                'soy': [p for p in pests if any(c['crops'] == 'соя' for c in pest_crops if c['vermin_id'] == p['id'])],
                'sugar_beet': [p for p in pests if any(c['crops'] == 'сахарная свекла' for c in pest_crops if c['vermin_id'] == p['id'])],
                'sunflower': [p for p in pests if any(c['crops'] == 'подсолнечник' for c in pest_crops if c['vermin_id'] == p['id'])],
                'pea_nut': [p for p in pests if any(c['crops'] in ['горох', 'нут'] for c in pest_crops if c['vermin_id'] == p['id'])],
                'flax': [p for p in pests if any(c['crops'] == 'лен' for c in pest_crops if c['vermin_id'] == p['id'])],
                'potato': [p for p in pests if any(c['crops'] == 'картофель' for c in pest_crops if c['vermin_id'] == p['id'])],
                'orchard': [p for p in pests if any(c['crops'] == 'садовые культуры' for c in pest_crops if c['vermin_id'] == p['id'])],
                'vineyard': [p for p in pests if any(c['crops'] == 'виноградники' for c in pest_crops if c['vermin_id'] == p['id'])]
            },
            'weeds': weeds
        }

        with open(os.path.join(OUTPUT_DIR, 'betaren_data.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"JSON-отчет сохранен в {os.path.join(OUTPUT_DIR, 'betaren_data.json')}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении JSON-отчета: {e}")

if __name__ == "__main__":
    main()