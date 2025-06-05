#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import csv
import os
import json
import uuid
import logging
import time
import random
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Загрузка настроек
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("betaren_fixed.log", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BetarenFixed")

# Настройки из .env
OUTPUT_DIR = os.getenv('DOWNLOAD_DIR', 'downloads')
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', 'D:/crawler_risks/chromedriver.exe')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SLEEP_BETWEEN_REQUESTS = float(os.getenv('SLEEP_BETWEEN_REQUESTS', '2.0'))

# Константы
BASE_URL = "https://betaren.ru"
IMAGES_DIR = os.path.join(OUTPUT_DIR, 'images')

# User-Agent список
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.142 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15'
]


def create_directories():
    """Створення необхідних директорій"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

    for folder in ["diseases", "pests", "weeds"]:
        os.makedirs(os.path.join(IMAGES_DIR, folder), exist_ok=True)

    logger.info("✅ Директорії створено")


def get_webdriver():
    """Створення веб-драйвера"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)


def translate_text_gpt(text, target_language="ukrainian"):
    """Переклад тексту через OpenAI GPT API"""
    if not text or not text.strip() or not OPENAI_API_KEY:
        return ""

    try:
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        if target_language == "ukrainian":
            lang_instruction = "на українську мову"
        else:
            lang_instruction = "to English"

        prompt = f"Переведи этот текст {lang_instruction}, сохраняя научную терминологию:\n\n{text}"

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.2
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        translated_text = result['choices'][0]['message']['content'].strip()

        logger.info(f"✅ Переведено на {target_language}: {len(text)} -> {len(translated_text)} символов")
        return translated_text

    except Exception as e:
        logger.error(f"❌ Ошибка перевода: {e}")
        return ""


def download_image(image_url, filepath, referer=None):
    """Скачивание изображения"""
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': referer or BASE_URL
        }

        response = requests.get(image_url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()

        # Проверяем content-type
        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
            logger.warning(f"❌ Неподдерживаемый тип: {content_type}")
            return False

        # Создаем директорию
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Записываем файл
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Проверяем размер
        if os.path.getsize(filepath) < 1024:
            logger.warning(f"❌ Слишком маленький файл: {filepath}")
            os.remove(filepath)
            return False

        logger.info(f"✅ Изображение скачано: {os.path.basename(filepath)}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка скачивания {image_url}: {e}")
        return False


def extract_images_from_page(page_url):
    """Извлечение URL изображений со страницы"""
    driver = get_webdriver()

    try:
        logger.info(f"🔍 Ищем изображения на: {page_url}")
        driver.get(page_url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        image_urls = set()  # Используем set для уникальности

        # Приоритет 1: Основное изображение
        main_img = soup.select_one('div.harmful-detail__picture img.gallery__img')
        if main_img and main_img.get('src'):
            img_url = urljoin(page_url, main_img['src'])
            if not any(exclude in img_url.lower() for exclude in ['logo', 'icon', 'banner']):
                image_urls.add(img_url)
                logger.info(f"📸 Найдено основное изображение")

        # Приоритет 2: Галерея
        gallery_imgs = soup.select('div.harmful-detail__picture-gallery img.gallery__img')
        for img in gallery_imgs:
            if img.get('src'):
                img_url = urljoin(page_url, img['src'])
                if not any(exclude in img_url.lower() for exclude in ['logo', 'icon', 'banner']):
                    image_urls.add(img_url)

        # Приоритет 3: Ссылки на полноразмерные изображения
        gallery_links = soup.select('div.harmful-detail__picture-gallery a.gallery__link')
        for link in gallery_links:
            href = link.get('href', '')
            if any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                img_url = urljoin(page_url, href)
                image_urls.add(img_url)

        result = list(image_urls)
        logger.info(f"✅ Найдено {len(result)} уникальных изображений")
        return result

    except Exception as e:
        logger.error(f"❌ Ошибка извлечения изображений: {e}")
        return []
    finally:
        driver.quit()


def get_category_links(category_path):
    """Получение ссылок из категории с правильной фильтрацией"""
    driver = get_webdriver()

    try:
        full_url = f"{BASE_URL}{category_path}"
        logger.info(f"🔗 Собираем ссылки из: {full_url}")

        driver.get(full_url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Ищем только ссылки на конкретные элементы (не навигационные)
        links = []

        # Метод 1: Прямые ссылки в списке
        for link_elem in soup.find_all('a', href=True):
            href = link_elem['href']
            text = link_elem.get_text(strip=True)

            # Фильтры для правильных ссылок
            if (href.startswith('/harmful/') and
                    len(text) > 3 and
                    not any(exclude in href.lower() for exclude in [
                        'javascript:', 'mailto:', 'tel:', '#',
                        '/harmful/bolezni/', '/harmful/vrediteli/', '/harmful/sornyaki/',  # исключаем категории
                        'sitemap', 'search', 'login', 'register'
                    ]) and
                    # Исключаем навигационные тексты
                    not any(exclude in text.lower() for exclude in [
                        'заказать', 'order', 'главная', 'home', 'назад', 'back',
                        'меню', 'menu', 'поиск', 'search', 'войти', 'login'
                    ]) and
                    href != category_path):  # не сама категория

                full_item_url = urljoin(BASE_URL, href)
                links.append({
                    'name': text,
                    'url': full_item_url
                })

        # Удаляем дубликаты по URL
        seen_urls = set()
        unique_links = []
        for link in links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)

        logger.info(f"✅ Найдено {len(unique_links)} уникальных ссылок")
        return unique_links

    except Exception as e:
        logger.error(f"❌ Ошибка сбора ссылок: {e}")
        return []
    finally:
        driver.quit()


def scrape_detail_page(item_url, category_type):
    """Сбор детальной информации со страницы"""
    driver = get_webdriver()

    try:
        logger.info(f"📄 Обрабатываем: {item_url}")
        driver.get(item_url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Получаем название
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else ""

        if not title or len(title) < 3:
            logger.warning(f"❌ Некорректное название: '{title}'")
            return None

        # Собираем весь текстовый контент
        content_blocks = soup.find_all(['div', 'section'], class_=[
            'harmful-detail__content', 'content', 'description', 'text-content'
        ])

        all_text = ""
        for block in content_blocks:
            text = block.get_text(separator=' ', strip=True)
            if text and len(text) > 50:  # Только значимые блоки
                all_text += text + " "

        # Если основной контент не найден, берем из body
        if not all_text:
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if main_content:
                all_text = main_content.get_text(separator=' ', strip=True)

        # Разделяем текст на части по ключевым словам
        description_ru = ""
        symptoms_ru = ""
        development_conditions_ru = ""
        control_measures_ru = ""

        # Примитивное разделение текста
        text_parts = all_text.split('.')
        current_section = "description"

        for part in text_parts:
            part = part.strip()
            if len(part) < 10:
                continue

            # Определяем к какой секции относится текст
            part_lower = part.lower()

            if any(keyword in part_lower for keyword in ['симптом', 'признак', 'проявлен', 'поврежден']):
                current_section = "symptoms"
            elif any(keyword in part_lower for keyword in ['условия', 'развити', 'факторы', 'биолог']):
                current_section = "development"
            elif any(keyword in part_lower for keyword in ['защита', 'борьба', 'меры', 'контрол', 'препарат']):
                current_section = "control"

            # Добавляем к соответствующей секции
            if current_section == "description":
                description_ru += part + ". "
            elif current_section == "symptoms":
                symptoms_ru += part + ". "
            elif current_section == "development":
                development_conditions_ru += part + ". "
            elif current_section == "control":
                control_measures_ru += part + ". "

        # Если не удалось разделить, используем весь текст как описание
        if not any([description_ru, symptoms_ru, development_conditions_ru, control_measures_ru]):
            description_ru = all_text[:1000] if all_text else ""  # Первые 1000 символов

        # Переводы
        logger.info("🌍 Выполняем переводы...")

        description_ua = translate_text_gpt(description_ru, "ukrainian") if description_ru else ""
        description_en = translate_text_gpt(description_ru, "english") if description_ru else ""

        symptoms_ua = translate_text_gpt(symptoms_ru, "ukrainian") if symptoms_ru else ""
        symptoms_en = translate_text_gpt(symptoms_ru, "english") if symptoms_ru else ""

        development_conditions_ua = translate_text_gpt(development_conditions_ru,
                                                       "ukrainian") if development_conditions_ru else ""
        development_conditions_en = translate_text_gpt(development_conditions_ru,
                                                       "english") if development_conditions_ru else ""

        control_measures_ua = translate_text_gpt(control_measures_ru, "ukrainian") if control_measures_ru else ""
        control_measures_en = translate_text_gpt(control_measures_ru, "english") if control_measures_ru else ""

        name_en = translate_text_gpt(title, "english") if title else ""

        # Небольшая пауза между API вызовами
        time.sleep(1)

        # Скачиваем изображения
        logger.info("📸 Скачиваем изображения...")
        image_urls = extract_images_from_page(item_url)

        item_id = str(uuid.uuid4())
        downloaded_images = []

        if image_urls:
            for i, image_url in enumerate(image_urls):
                # Генерируем имя файла
                parsed_url = urlparse(image_url)
                file_extension = os.path.splitext(parsed_url.path)[1] or '.jpg'

                # Очищаем название для файла
                clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                clean_title = clean_title.replace(' ', '_')[:30]  # Укорачиваем

                if len(image_urls) == 1:
                    filename = f"{category_type}_{clean_title}_{item_id[:8]}{file_extension}"
                else:
                    filename = f"{category_type}_{clean_title}_{item_id[:8]}_{i + 1:02d}{file_extension}"

                filepath = os.path.join(IMAGES_DIR, category_type, filename)

                # Скачиваем
                if download_image(image_url, filepath, item_url):
                    downloaded_images.append({
                        'image_url': image_url,
                        'image_path': filepath,
                        'filename': filename
                    })

                time.sleep(random.uniform(0.5, 1.0))

        # Определяем культуры (базовый список)
        crops = []
        full_text_lower = all_text.lower()
        common_crops = ['пшеница', 'рожь', 'ячмень', 'овес', 'кукуруза', 'подсолнечник', 'соя', 'рапс']

        for crop in common_crops:
            if crop in full_text_lower:
                crops.append(crop)

        if not crops:  # Если не найдено, добавляем пшеницу по умолчанию
            crops = ['пшеница']

        result = {
            'id': item_id,
            'name': title,
            'name_en': name_en,
            'scientific_name': "",  # Можно дополнительно извлекать
            'description_ru': description_ru.strip(),
            'description_ua': description_ua.strip(),
            'description_en': description_en.strip(),
            'symptoms_ru': symptoms_ru.strip(),
            'symptoms_ua': symptoms_ua.strip(),
            'symptoms_en': symptoms_en.strip(),
            'development_conditions_ru': development_conditions_ru.strip(),
            'development_conditions_ua': development_conditions_ua.strip(),
            'development_conditions_en': development_conditions_en.strip(),
            'control_measures_ru': control_measures_ru.strip(),
            'control_measures_ua': control_measures_ua.strip(),
            'control_measures_en': control_measures_en.strip(),
            'source_urls': item_url,
            'crops': crops,
            'images': downloaded_images,
            'is_active': True,
            'version': 1
        }

        logger.info(f"✅ Успешно обработано: {title}")
        return result

    except Exception as e:
        logger.error(f"❌ Ошибка обработки {item_url}: {e}")
        return None
    finally:
        driver.quit()


def save_data_to_csv(data, category_type):
    """Сохранение данных в CSV файлы согласно схеме БД"""
    if not data:
        logger.warning(f"❌ Нет данных для сохранения в {category_type}")
        return

    logger.info(f"💾 Сохраняем {len(data)} записей для {category_type}")

    # Маппинг типов категорий к названиям таблиц БД
    table_mapping = {
        'diseases': 'disease',
        'pests': 'vermin',
        'weeds': 'weed'
    }

    table_name = table_mapping.get(category_type, category_type[:-1])

    # Файлы CSV
    main_csv = os.path.join(OUTPUT_DIR, f'{category_type}.csv')
    descriptions_csv = os.path.join(OUTPUT_DIR, f'{table_name}_descriptions.csv')
    images_csv = os.path.join(OUTPUT_DIR, f'{table_name}_images.csv')
    crops_csv = os.path.join(OUTPUT_DIR, f'{table_name}_crops.csv')

    # 1. Основная таблица
    with open(main_csv, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['id', 'name', 'name_en', 'scientific_name', 'is_active']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            writer.writerow({
                'id': item['id'],
                'name': item['name'],
                'name_en': item['name_en'],
                'scientific_name': item['scientific_name'],
                'is_active': item['is_active']
            })

    # 2. Таблица описаний (согласно схеме БД)
    with open(descriptions_csv, 'w', encoding='utf-8', newline='') as f:
        if category_type == 'diseases':
            fieldnames = [
                'id', 'disease_id', 'description_ru', 'description_ua', 'description_en',
                'symptoms_ru', 'symptoms_ua', 'symptoms_en',
                'development_conditions_ru', 'development_conditions_ua', 'development_conditions_en',
                'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                'photo_path', 'version'
            ]
        elif category_type == 'pests':
            fieldnames = [
                'id', 'vermin_id', 'description_ru', 'description_ua', 'description_en',
                'damage_symptoms_ru', 'damage_symptoms_ua', 'damage_symptoms_en',
                'biology_ru', 'biology_ua', 'biology_en',
                'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                'photo_path', 'version'
            ]
        else:  # weeds
            fieldnames = [
                'id', 'weed_id', 'description_ru', 'description_ua', 'description_en',
                'biological_features_ru', 'biological_features_ua', 'biological_features_en',
                'harmfulness_ru', 'harmfulness_ua', 'harmfulness_en',
                'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                'photo_path', 'version'
            ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            # Путь к основному фото
            main_photo_path = item['images'][0]['image_path'] if item['images'] else ""

            base_row = {
                'id': str(uuid.uuid4()),
                f'{table_name}_id': item['id'],
                'description_ru': item['description_ru'],
                'description_ua': item['description_ua'],
                'description_en': item['description_en'],
                'control_measures_ru': item['control_measures_ru'],
                'control_measures_ua': item['control_measures_ua'],
                'control_measures_en': item['control_measures_en'],
                'photo_path': main_photo_path,
                'version': item['version']
            }

            if category_type == 'diseases':
                base_row.update({
                    'symptoms_ru': item['symptoms_ru'],
                    'symptoms_ua': item['symptoms_ua'],
                    'symptoms_en': item['symptoms_en'],
                    'development_conditions_ru': item['development_conditions_ru'],
                    'development_conditions_ua': item['development_conditions_ua'],
                    'development_conditions_en': item['development_conditions_en']
                })
            elif category_type == 'pests':
                base_row.update({
                    'damage_symptoms_ru': item['symptoms_ru'],
                    'damage_symptoms_ua': item['symptoms_ua'],
                    'damage_symptoms_en': item['symptoms_en'],
                    'biology_ru': item['development_conditions_ru'],
                    'biology_ua': item['development_conditions_ua'],
                    'biology_en': item['development_conditions_en']
                })
            else:  # weeds
                base_row.update({
                    'biological_features_ru': item['symptoms_ru'],
                    'biological_features_ua': item['symptoms_ua'],
                    'biological_features_en': item['symptoms_en'],
                    'harmfulness_ru': item['development_conditions_ru'],
                    'harmfulness_ua': item['development_conditions_ua'],
                    'harmfulness_en': item['development_conditions_en']
                })

            writer.writerow(base_row)

    # 3. Таблица изображений
    with open(images_csv, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['id', f'{table_name}_id', 'image_path', 'image_url', 'version']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            for image in item['images']:
                writer.writerow({
                    'id': str(uuid.uuid4()),
                    f'{table_name}_id': item['id'],
                    'image_path': image['image_path'],
                    'image_url': image['image_url'],
                    'version': 1
                })

    # 4. Таблица культур
    with open(crops_csv, 'w', encoding='utf-8', newline='') as f:
        fieldnames = [f'{table_name}_id', 'crops']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            for crop in item['crops']:
                writer.writerow({
                    f'{table_name}_id': item['id'],
                    'crops': crop
                })

    logger.info(f"✅ Данные сохранены в 4 CSV файла для {category_type}")


def process_category(category_type, max_items=None):
    """Обработка одной категории"""
    logger.info(f"🚀 Начинаем обработку категории: {category_type}")

    # Определяем пути для категорий
    category_paths = {
        'diseases': [
            '/harmful/bolezni/bolezni-zernovykh-kultur/',
            '/harmful/bolezni/bolezni-sadovyh-kultur/',
            '/harmful/bolezni/bolezni-ovoshchnyh-kultur/'
        ],
        'pests': [
            '/harmful/vrediteli/vrediteli-zernovykh-kultur/',
            '/harmful/vrediteli/vrediteli-sadovyh-kultur/',
            '/harmful/vrediteli/vrediteli-ovoshchnyh-kultur/'
        ],
        'weeds': [
            '/harmful/sornyaki/'
        ]
    }

    # Собираем ссылки из всех подкategorий
    all_links = []
    paths = category_paths.get(category_type, [])

    for path in paths:
        logger.info(f"📂 Обрабатываем подкатегорию: {path}")
        links = get_category_links(path)
        all_links.extend(links)
        time.sleep(2)  # Пауза между подкатегориями

    # Удаляем дубликаты
    seen_urls = set()
    unique_links = []
    for link in all_links:
        if link['url'] not in seen_urls:
            seen_urls.add(link['url'])
            unique_links.append(link)

    logger.info(f"📊 Всего найдено {len(unique_links)} уникальных ссылок для {category_type}")

    if max_items and len(unique_links) > max_items:
        unique_links = unique_links[:max_items]
        logger.info(f"⚠️ Ограничиваем до {max_items} элементов")

    # Обрабатываем каждую ссылку
    processed_data = []

    for i, link in enumerate(unique_links, 1):
        logger.info(f"📄 [{i}/{len(unique_links)}] Обрабатываем: {link['name']}")

        try:
            detail_data = scrape_detail_page(link['url'], category_type)

            if detail_data:
                processed_data.append(detail_data)
                logger.info(f"✅ Успешно обработано: {detail_data['name']}")

                # Промежуточное сохранение каждые 5 элементов
                if len(processed_data) % 5 == 0:
                    logger.info(f"💾 Промежуточное сохранение: {len(processed_data)} элементов")
                    save_data_to_csv(processed_data, category_type)
            else:
                logger.warning(f"❌ Не удалось обработать: {link['name']}")

            # Пауза между запросами
            time.sleep(SLEEP_BETWEEN_REQUESTS)

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке {link['name']}: {e}")
            continue

    # Финальное сохранение
    if processed_data:
        save_data_to_csv(processed_data, category_type)
        logger.info(f"🎉 Категория {category_type} завершена! Обработано: {len(processed_data)} элементов")
    else:
        logger.warning(f"❌ Нет данных для сохранения в категории {category_type}")

    return processed_data


def main():
    """Основная функция"""
    print("🔧 ИСПРАВЛЕННЫЙ скрапер Betaren.ru")
    print("   ✅ Правильная фильтрация ссылок")
    print("   ✅ Корректное извлечение контента")
    print("   ✅ Рабочие переводы через GPT")
    print("   ✅ Скачивание изображений")
    print("   ✅ Правильная схема БД")
    print()
    print("1. Обработать ВСЕ категории (болезни + вредители + сорняки)")
    print("2. Только болезни")
    print("3. Только вредители")
    print("4. Только сорняки")
    print("5. ТЕСТ: по 3 элемента из каждой категории")

    choice = input("\nВыберите опцию (1-5): ").strip()

    # Проверяем настройки
    if not OPENAI_API_KEY:
        logger.warning("⚠️ OpenAI API ключ не найден - переводы будут пропущены")
        proceed = input("Продолжить без переводов? (y/n): ").strip().lower()
        if proceed != 'y':
            return

    create_directories()

    if choice == "1":
        logger.info("🚀 Обрабатываем ВСЕ категории")
        process_category('diseases')
        process_category('pests')
        process_category('weeds')

    elif choice == "2":
        logger.info("🦠 Обрабатываем только болезни")
        process_category('diseases')

    elif choice == "3":
        logger.info("🐛 Обрабатываем только вредителей")
        process_category('pests')

    elif choice == "4":
        logger.info("🌱 Обрабатываем только сорняки")
        process_category('weeds')

    elif choice == "5":
        logger.info("🧪 ТЕСТОВЫЙ режим: по 3 элемента")
        process_category('diseases', max_items=3)
        process_category('pests', max_items=3)
        process_category('weeds', max_items=3)

    else:
        print("❌ Некорректный выбор")
        return

    print("\n🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
    print(f"📁 Результаты в папке: {OUTPUT_DIR}")
    print(f"🖼️ Изображения в папке: {IMAGES_DIR}")
    print("📊 CSV файлы готовы для загрузки в БД!")


if __name__ == "__main__":
    main()