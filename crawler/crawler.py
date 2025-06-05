#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import time
import uuid
import logging
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import dotenv
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import socket
import socks
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Загрузка переменных окружения
dotenv.load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("../agriscouting_parse_log.txt", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("agriscouting_parse")

# Папка для результатов
OUTPUT_DIR = "../agriscouting_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)
for folder in ["diseases", "pests", "weeds"]:
    os.makedirs(os.path.join(OUTPUT_DIR, "images", folder), exist_ok=True)

# Настройка прокси
proxy_url = os.getenv("HTTP_PROXY", "")
if proxy_url:
    logger.info(f"Используется прокси: {proxy_url}")
    parsed_proxy = urlparse(proxy_url)
    proxy_host = parsed_proxy.hostname
    proxy_port = parsed_proxy.port or 8080
    proxies = {"http": proxy_url, "https": proxy_url}
    if parsed_proxy.scheme == 'socks5':
        socks.set_default_proxy(socks.SOCKS5, proxy_host, proxy_port, username=parsed_proxy.username, password=parsed_proxy.password)
        socket.socket = socks.socksocket
else:
    proxies = None
    logger.info("Прокси не используется. Для доступа к .ru используйте VPN.")

# User-Agents для эмуляции браузера
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.2 Safari/605.1.15',
]

# Культуры для связи (на основе исходного скрипта)
crop_guids = {
    "пшеница": "501933b1-b43d-11e9-a3c5-00155d012200",
    "ячмень": "e399a8a8-3441-4478-9d3e-7871dcbaf4cc",
    "кукуруза": "c61ecabe-229e-4361-921a-081125d5c3c1",
    "соя": "779e1399-c6b2-11ec-a40a-0050568c4a92",
    # Добавьте другие культуры по необходимости
}

ua_crops = {
    "пшеница": "пшениця",
    "ячмень": "ячмінь",
    "кукуруза": "кукурудза",
    "соя": "соя",
}

target_crops = {
    "wheat": "пшеница",
    "barley": "ячмень",
    "corn": "кукуруза",
    "soybean": "соя",
}

# Целевые сайты
TARGET_SITES = {
    "diseases": [
        {"url": "https://www.syngenta.by/bolezni-zernovyh-kultur", "crops": ["пшеница", "ячмень"]},
        {"url": "https://betaren.ru/harmful/bolezni/", "crops": ["пшеница", "ячмень", "кукуруза", "соя"]},
    ],
    "pests": [
        {"url": "https://betaren.ru/harmful/vrediteli/", "crops": ["пшеница", "ячмень", "кукуруза", "соя"]},
    ],
    "weeds": [
        {"url": "https://betaren.ru/harmful/sornyaki/", "crops": ["пшеница", "ячмень", "кукуруза", "соя"]},
    ]
}

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_soup_from_url(url, max_retries=3):
    for retry in range(max_retries):
        try:
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8,uk;q=0.7',
                'Referer': 'https://www.google.com/'
            }
            response = requests.get(url, headers=headers, timeout=15, proxies=proxies, verify=False)
            logger.info(f"Запрос: {url} | Статус: {response.status_code}")
            if response.status_code == 200:
                if 'captcha' in response.text.lower():
                    logger.warning(f"Обнаружена CAPTCHA на {url}")
                    time.sleep(5)
                    continue
                encoding = response.encoding if response.encoding != 'ISO-8859-1' else 'utf-8'
                return BeautifulSoup(response.content, 'html.parser', from_encoding=encoding)
            elif response.status_code in [403, 429]:
                logger.warning(f"Ошибка {response.status_code} на {url}")
                time.sleep(2 + retry)
            else:
                logger.warning(f"Ошибка {response.status_code} на {url}")
                return None
        except Exception as e:
            logger.error(f"Ошибка при запросе {url}: {e}")
            time.sleep(2 + retry)
    logger.error(f"Не удалось получить {url} после {max_retries} попыток")
    return None

def translate_text(text, target_lang):
    # Заглушка для перевода (замените на OpenAI API при необходимости)
    if not text:
        return ""
    if target_lang == "ru":
        return text
    elif target_lang == "ua":
        return f"[UA] {text[:100]}..." if len(text) > 100 else f"[UA] {text}"
    elif target_lang == "en":
        return f"[EN] {text[:100]}..." if len(text) > 100 else f"[EN] {text}"
    return text

def download_image(url, folder, filename, source_url):
    file_path = os.path.join(OUTPUT_DIR, "images", folder, filename)
    if url.startswith('//'):
        url = 'https:' + url
    if not url.startswith('http'):
        base_url = f"{urlparse(source_url).scheme}://{urlparse(source_url).netloc}"
        url = urljoin(base_url, url)
    try:
        headers = {'User-Agent': get_random_user_agent(), 'Referer': source_url}
        response = requests.get(url, headers=headers, timeout=10, proxies=proxies, verify=False)
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            with open(file_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Изображение скачано: {file_path}")
            return file_path
        logger.warning(f"Ошибка скачивания изображения: {url}")
    except Exception as e:
        logger.error(f"Ошибка при скачивании {url}: {e}")
    return None

def parse_syngenta_diseases(base_url, crops):
    diseases = []
    descriptions = []
    images = []
    disease_crops = []
    soup = get_soup_from_url(base_url)
    if not soup:
        return [], [], [], []

    # Находим ссылки на болезни
    links = soup.select('a[href*="/bolezni-zernovyh-kultur/"]')
    for link in tqdm(links, desc="Парсинг болезней Syngenta"):
        href = link.get('href')
        if not href:
            continue
        full_url = urljoin(base_url, href)
        detail_soup = get_soup_from_url(full_url)
        if not detail_soup:
            continue

        # Извлечение данных
        name_ru = detail_soup.select_one('h1').get_text().strip() if detail_soup.select_one('h1') else ""
        name_en = translate_text(name_ru, "en")
        disease_id = str(uuid.uuid4())

        content = detail_soup.select_one('.content, .disease-detail, article')
        description = ""
        symptoms = ""
        conditions = ""
        measures = ""
        if content:
            sections = content.select('h2, h3, p')
            current_section = None
            for elem in sections:
                text = elem.get_text().strip().lower()
                if elem.name in ['h2', 'h3']:
                    if 'симптомы' in text:
                        current_section = 'symptoms'
                    elif 'условия' in text or 'распространение' in text:
                        current_section = 'conditions'
                    elif 'меры' in text or 'контроль' in text:
                        current_section = 'measures'
                    else:
                        current_section = 'description'
                elif elem.name == 'p' and current_section:
                    if current_section == 'description':
                        description += elem.get_text().strip() + " "
                    elif current_section == 'symptoms':
                        symptoms += elem.get_text().strip() + " "
                    elif current_section == 'conditions':
                        conditions += elem.get_text().strip() + " "
                    elif current_section == 'measures':
                        measures += elem.get_text().strip() + " "

        # Изображения
        img_tags = detail_soup.select('img[src]')
        img_records = []
        for i, img in enumerate(img_tags[:5]):
            img_url = img.get('src')
            if not img_url:
                continue
            filename = f"disease_{disease_id}_{i+1}.jpg"
            img_path = download_image(img_url, "diseases", filename, full_url)
            if img_path:
                img_records.append({
                    "id": str(uuid.uuid4()),
                    "disease_id": disease_id,
                    "image_url": img_url,
                    "image_path": img_path,
                    "caption": img.get('alt', ''),
                    "source": "Syngenta",
                    "source_url": full_url
                })

        # Формирование данных
        diseases.append({
            "id": disease_id,
            "name": name_ru,
            "name_en": name_en,
            "scientific_name": "",
            "is_active": True
        })
        descriptions.append({
            "id": str(uuid.uuid4()),
            "disease_id": disease_id,
            "description_ru": description.strip(),
            "description_ua": translate_text(description, "ua"),
            "description_en": translate_text(description, "en"),
            "symptoms_ru": symptoms.strip(),
            "symptoms_ua": translate_text(symptoms, "ua"),
            "symptoms_en": translate_text(symptoms, "en"),
            "development_conditions_ru": conditions.strip(),
            "development_conditions_ua": translate_text(conditions, "ua"),
            "development_conditions_en": translate_text(conditions, "en"),
            "control_measures_ru": measures.strip(),
            "control_measures_ua": translate_text(measures, "ua"),
            "control_measures_en": translate_text(measures, "en"),
            "photo_path": img_records[0]["image_path"] if img_records else "",
            "source_urls": full_url
        })
        images.extend(img_records)
        for crop in crops:
            disease_crops.append({"disease_id": disease_id, "crops": crop})

    return diseases, descriptions, images, disease_crops

def parse_betaren(base_url, data_type, crops):
    items = []
    descriptions = []
    images = []
    item_crops = []
    soup = get_soup_from_url(base_url)
    if not soup:
        return [], [], [], []

    # Находим ссылки на элементы
    selector = 'a[href*="/harmful/"]'
    links = soup.select(selector)
    for link in tqdm(links, desc=f"Парсинг {data_type} Betaren"):
        href = link.get('href')
        if not href:
            continue
        full_url = urljoin(base_url, href)
        detail_soup = get_soup_from_url(full_url)
        if not detail_soup:
            continue

        # Извлечение данных
        name_ru = detail_soup.select_one('h1').get_text().strip() if detail_soup.select_one('h1') else ""
        name_en = translate_text(name_ru, "en")
        item_id = str(uuid.uuid4())

        content = detail_soup.select_one('.content, .entry-content, article')
        description = ""
        symptoms = ""
        conditions = ""
        measures = ""
        biology = ""
        harmfulness = ""
        if content:
            sections = content.select('h2, h3, p')
            current_section = None
            for elem in sections:
                text = elem.get_text().strip().lower()
                if elem.name in ['h2', 'h3']:
                    if 'симптомы' in text or 'признаки' in text:
                        current_section = 'symptoms'
                    elif 'условия' in text or 'распространение' in text:
                        current_section = 'conditions'
                    elif 'меры' in text or 'контроль' in text:
                        current_section = 'measures'
                    elif 'биология' in text or 'жизненный цикл' in text:
                        current_section = 'biology'
                    elif 'вред' in text or 'вредоносность' in text:
                        current_section = 'harmfulness'
                    else:
                        current_section = 'description'
                elif elem.name == 'p' and current_section:
                    if current_section == 'description':
                        description += elem.get_text().strip() + " "
                    elif current_section == 'symptoms':
                        symptoms += elem.get_text().strip() + " "
                    elif current_section == 'conditions':
                        conditions += elem.get_text().strip() + " "
                    elif current_section == 'measures':
                        measures += elem.get_text().strip() + " "
                    elif current_section == 'biology':
                        biology += elem.get_text().strip() + " "
                    elif current_section == 'harmfulness':
                        harmfulness += elem.get_text().strip() + " "

        # Изображения
        img_tags = detail_soup.select('img[src]')
        img_records = []
        for i, img in enumerate(img_tags[:5]):
            img_url = img.get('src')
            if not img_url:
                continue
            filename = f"{data_type}_{item_id}_{i+1}.jpg"
            img_path = download_image(img_url, data_type, filename, full_url)
            if img_path:
                img_records.append({
                    "id": str(uuid.uuid4()),
                    f"{data_type[:-1]}_id": item_id,
                    "image_url": img_url,
                    "image_path": img_path,
                    "caption": img.get('alt', ''),
                    "source": "Betaren",
                    "source_url": full_url
                })

        # Формирование данных
        items.append({
            "id": item_id,
            "name": name_ru,
            "name_en": name_en,
            "scientific_name": "",
            "is_active": True
        })
        if data_type == "diseases":
            descriptions.append({
                "id": str(uuid.uuid4()),
                "disease_id": item_id,
                "description_ru": description.strip(),
                "description_ua": translate_text(description, "ua"),
                "description_en": translate_text(description, "en"),
                "symptoms_ru": symptoms.strip(),
                "symptoms_ua": translate_text(symptoms, "ua"),
                "symptoms_en": translate_text(symptoms, "en"),
                "development_conditions_ru": conditions.strip(),
                "development_conditions_ua": translate_text(conditions, "ua"),
                "development_conditions_en": translate_text(conditions, "en"),
                "control_measures_ru": measures.strip(),
                "control_measures_ua": translate_text(measures, "ua"),
                "control_measures_en": translate_text(measures, "en"),
                "photo_path": img_records[0]["image_path"] if img_records else "",
                "source_urls": full_url
            })
        elif data_type == "pests":
            descriptions.append({
                "id": str(uuid.uuid4()),
                "vermin_id": item_id,
                "description_ru": description.strip(),
                "description_ua": translate_text(description, "ua"),
                "description_en": translate_text(description, "en"),
                "damage_symptoms_ru": symptoms.strip() or harmfulness.strip(),
                "damage_symptoms_ua": translate_text(symptoms or harmfulness, "ua"),
                "damage_symptoms_en": translate_text(symptoms or harmfulness, "en"),
                "biology_ru": biology.strip(),
                "biology_ua": translate_text(biology, "ua"),
                "biology_en": translate_text(biology, "en"),
                "control_measures_ru": measures.strip(),
                "control_measures_ua": translate_text(measures, "ua"),
                "control_measures_en": translate_text(measures, "en"),
                "photo_path": img_records[0]["image_path"] if img_records else "",
                "source_urls": full_url
            })
        elif data_type == "weeds":
            descriptions.append({
                "id": str(uuid.uuid4()),
                "weed_id": item_id,
                "description_ru": description.strip(),
                "description_ua": translate_text(description, "ua"),
                "description_en": translate_text(description, "en"),
                "biological_features_ru": biology.strip(),
                "biological_features_ua": translate_text(biology, "ua"),
                "biological_features_en": translate_text(biology, "en"),
                "harmfulness_ru": harmfulness.strip() or symptoms.strip(),
                "harmfulness_ua": translate_text(harmfulness or symptoms, "ua"),
                "harmfulness_en": translate_text(harmfulness or symptoms, "en"),
                "control_measures_ru": measures.strip(),
                "control_measures_ua": translate_text(measures, "ua"),
                "control_measures_en": translate_text(measures, "en"),
                "photo_path": img_records[0]["image_path"] if img_records else "",
                "source_urls": full_url
            })
        images.extend(img_records)
        for crop in crops:
            item_crops.append({f"{data_type[:-1]}_id": item_id, "crops": crop})

    return items, descriptions, images, item_crops

def save_to_csv(data, filename, fieldnames):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                safe_row = {k: str(row.get(k, '')) for k in fieldnames}
                writer.writerow(safe_row)
        logger.info(f"Сохранено в {filename}: {len(data)} записей")
    except Exception as e:
        logger.error(f"Ошибка сохранения в {filename}: {e}")

def main():
    logger.info("Запуск парсинга данных для AgriScouting")

    # Инициализация данных
    all_diseases = []
    all_disease_descriptions = []
    all_disease_images = []
    all_disease_crops = []
    all_pests = []
    all_pest_descriptions = []
    all_pest_images = []
    all_pest_crops = []
    all_weeds = []
    all_weed_descriptions = []
    all_weed_images = []
    all_weed_crops = []

    # Парсинг Syngenta
    for site in TARGET_SITES["diseases"]:
        if "syngenta.by" in site["url"]:
            diseases, descriptions, images, crops = parse_syngenta_diseases(site["url"], site["crops"])
            all_diseases.extend(diseases)
            all_disease_descriptions.extend(descriptions)
            all_disease_images.extend(images)
            all_disease_crops.extend(crops)

    # Парсинг Betaren
    for data_type, sites in TARGET_SITES.items():
        for site in sites:
            if "betaren.ru" in site["url"]:
                items, descriptions, images, crops = parse_betaren(site["url"], data_type, site["crops"])
                if data_type == "diseases":
                    all_diseases.extend(items)
                    all_disease_descriptions.extend(descriptions)
                    all_disease_images.extend(images)
                    all_disease_crops.extend(crops)
                elif data_type == "pests":
                    all_pests.extend(items)
                    all_pest_descriptions.extend(descriptions)
                    all_pest_images.extend(images)
                    all_pest_crops.extend(crops)
                elif data_type == "weeds":
                    all_weeds.extend(items)
                    all_weed_descriptions.extend(descriptions)
                    all_weed_images.extend(images)
                    all_weed_crops.extend(crops)

    # Сохранение в CSV
    save_to_csv(all_diseases, os.path.join(OUTPUT_DIR, "diseases.csv"),
                ["id", "name", "name_en", "scientific_name", "is_active"])
    save_to_csv(all_disease_descriptions, os.path.join(OUTPUT_DIR, "disease_descriptions.csv"),
                ["id", "disease_id", "description_ru", "description_ua", "description_en",
                 "symptoms_ru", "symptoms_ua", "symptoms_en",
                 "development_conditions_ru", "development_conditions_ua", "development_conditions_en",
                 "control_measures_ru", "control_measures_ua", "control_measures_en",
                 "photo_path", "source_urls"])
    save_to_csv(all_disease_images, os.path.join(OUTPUT_DIR, "disease_images.csv"),
                ["id", "disease_id", "image_url", "image_path", "caption", "source", "source_url"])
    save_to_csv(all_disease_crops, os.path.join(OUTPUT_DIR, "disease_crops.csv"),
                ["disease_id", "crops"])

    save_to_csv(all_pests, os.path.join(OUTPUT_DIR, "vermins.csv"),
                ["id", "name", "name_en", "scientific_name", "is_active"])
    save_to_csv(all_pest_descriptions, os.path.join(OUTPUT_DIR, "vermin_descriptions.csv"),
                ["id", "vermin_id", "description_ru", "description_ua", "description_en",
                 "damage_symptoms_ru", "damage_symptoms_ua", "damage_symptoms_en",
                 "biology_ru", "biology_ua", "biology_en",
                 "control_measures_ru", "control_measures_ua", "control_measures_en",
                 "photo_path", "source_urls"])
    save_to_csv(all_pest_images, os.path.join(OUTPUT_DIR, "vermin_images.csv"),
                ["id", "vermin_id", "image_url", "image_path", "caption", "source", "source_url"])
    save_to_csv(all_pest_crops, os.path.join(OUTPUT_DIR, "vermin_crops.csv"),
                ["vermin_id", "crops"])

    save_to_csv(all_weeds, os.path.join(OUTPUT_DIR, "weeds.csv"),
                ["id", "name", "name_en", "scientific_name", "is_active"])
    save_to_csv(all_weed_descriptions, os.path.join(OUTPUT_DIR, "weed_descriptions.csv"),
                ["id", "weed_id", "description_ru", "description_ua", "description_en",
                 "biological_features_ru", "biological_features_ua", "biological_features_en",
                 "harmfulness_ru", "harmfulness_ua", "harmfulness_en",
                 "control_measures_ru", "control_measures_ua", "control_measures_en",
                 "photo_path", "source_urls"])
    save_to_csv(all_weed_images, os.path.join(OUTPUT_DIR, "weed_images.csv"),
                ["id", "weed_id", "image_url", "image_path", "caption", "source", "source_url"])
    save_to_csv(all_weed_crops, os.path.join(OUTPUT_DIR, "weed_crops.csv"),
                ["weed_id", "crops"])

    logger.info("Парсинг завершен. Данные сохранены в CSV.")

if __name__ == "__main__":
    main()