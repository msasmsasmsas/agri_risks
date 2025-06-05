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
        logging.FileHandler("betaren_universal.log", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BetarenUniversal")

# Настройки
OUTPUT_DIR = os.getenv('DOWNLOAD_DIR', 'downloads')
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', 'chromedriver.exe')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SLEEP_BETWEEN_REQUESTS = float(os.getenv('SLEEP_BETWEEN_REQUESTS', '2.0'))

BASE_URL = "https://betaren.ru"
IMAGES_DIR = os.path.join(OUTPUT_DIR, 'images')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]


def create_directories():
    """Создание необходимых директорий"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    for folder in ["diseases", "pests", "weeds"]:
        os.makedirs(os.path.join(IMAGES_DIR, folder), exist_ok=True)
    logger.info("✅ Директории созданы")


def get_webdriver():
    """Создание веб-драйвера"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def translate_text_gpt(text, target_language="ukrainian"):
    """Перевод текста через OpenAI GPT API"""
    if not text or not text.strip() or not OPENAI_API_KEY:
        return ""

    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        if target_language == "ukrainian":
            prompt = f"Переведи этот текст на украинский язык, сохраняя научную терминологию:\n\n{text}"
        else:
            prompt = f"Translate this text to English, preserving scientific terminology:\n\n{text}"

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

        logger.info(f"✅ Переведено на {target_language}")
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
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Referer': referer or BASE_URL
        }

        response = requests.get(image_url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
            logger.warning(f"❌ Неподдерживаемый тип: {content_type}")
            return False

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if os.path.getsize(filepath) < 1024:
            logger.warning(f"❌ Слишком маленький файл")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False

        logger.info(f"✅ Изображение скачано: {os.path.basename(filepath)}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка скачивания {image_url}: {e}")
        return False


def extract_images_from_page(soup, page_url):
    """Извлечение изображений со страницы на основе РЕАЛЬНОЙ структуры HTML"""
    try:
        image_urls = []

        # 1. ОСНОВНОЕ ИЗОБРАЖЕНИЕ из div.harmful-detail__picture img
        main_img = soup.select_one('div.harmful-detail__picture img')
        if main_img and main_img.get('src'):
            img_url = urljoin(page_url, main_img['src'])
            image_urls.append(img_url)
            logger.info(f"📸 Найдено основное изображение")

        # 2. ГАЛЕРЕЯ ИЗОБРАЖЕНИЙ из swiper-slide
        gallery_imgs = soup.select('div.swiper-slide img.gallery__img')
        for img in gallery_imgs:
            if img.get('src'):
                img_url = urljoin(page_url, img['src'])
                if img_url not in image_urls:
                    image_urls.append(img_url)

        # 3. ССЫЛКИ НА ПОЛНОРАЗМЕРНЫЕ ИЗОБРАЖЕНИЯ
        gallery_links = soup.select('a.gallery__link[href]')
        for link in gallery_links:
            href = link.get('href', '')
            if any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                img_url = urljoin(page_url, href)
                if img_url not in image_urls:
                    image_urls.append(img_url)

        # 4. ДОПОЛНИТЕЛЬНЫЙ ПОИСК - любые img в контенте
        content_imgs = soup.select('div.content img, div.harmful-detail img, img')
        for img in content_imgs:
            if img.get('src'):
                img_url = urljoin(page_url, img['src'])
                if img_url not in image_urls and any(
                        ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    image_urls.append(img_url)

        logger.info(f"✅ Найдено {len(image_urls)} изображений")
        return image_urls

    except Exception as e:
        logger.error(f"❌ Ошибка извлечения изображений: {e}")
        return []


def parse_content_from_html(soup):
    """Парсинг контента на основе РЕАЛЬНОЙ структуры HTML"""
    try:
        # НАЗВАНИЕ из H1
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else ""

        # НАУЧНОЕ НАЗВАНИЕ
        scientific_name = ""
        detail_text = soup.find('div', class_='harmful-detail__text')
        if detail_text:
            italic_text = detail_text.find('i')
            if italic_text:
                scientific_name = italic_text.get_text(strip=True)

        # ВЕСЬ ТЕКСТОВЫЙ КОНТЕНТ
        all_content = ""
        if detail_text:
            paragraphs = detail_text.find_all(['p', 'div', 'h3'])
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 10:
                    all_content += text + "\n\n"

        if not all_content:
            content_area = soup.find('div', class_='content__inner') or soup.find('main')
            if content_area:
                all_content = content_area.get_text(separator='\n\n', strip=True)

        # РАЗБИВАЕМ КОНТЕНТ НА СЕКЦИИ
        content_lines = all_content.split('\n\n')

        description_ru = ""
        symptoms_ru = ""
        development_conditions_ru = ""
        control_measures_ru = ""

        current_section = "description"

        for line in content_lines:
            line = line.strip()
            if len(line) < 20:
                continue

            line_lower = line.lower()

            # Определяем секцию по заголовкам
            if any(keyword in line_lower for keyword in ['симптомы болезни', 'симптомы', 'признаки болезни']):
                current_section = "symptoms"
                continue
            elif any(keyword in line_lower for keyword in ['факторы', 'условия развития', 'развитие болезни']):
                current_section = "development"
                continue
            elif any(keyword in line_lower for keyword in ['меры защиты', 'меры борьбы', 'защита']):
                current_section = "control"
                continue

            # Добавляем контент к соответствующей секции
            if current_section == "description":
                description_ru += line + " "
            elif current_section == "symptoms":
                symptoms_ru += line + " "
            elif current_section == "development":
                development_conditions_ru += line + " "
            elif current_section == "control":
                control_measures_ru += line + " "

        # Если не удалось разделить, кладем весь текст в описание
        if not any([symptoms_ru, development_conditions_ru, control_measures_ru]):
            description_ru = all_content[:1500] if all_content else ""

        return {
            'title': title,
            'scientific_name': scientific_name,
            'description_ru': description_ru.strip(),
            'symptoms_ru': symptoms_ru.strip(),
            'development_conditions_ru': development_conditions_ru.strip(),
            'control_measures_ru': control_measures_ru.strip()
        }

    except Exception as e:
        logger.error(f"❌ Ошибка парсинга контента: {e}")
        return None


def get_subcategory_links(main_category_url):
    """Получение ссылок на подкатегории (культуры) или прямые ссылки на сорняки"""
    driver = get_webdriver()

    try:
        logger.info(f"🔗 Ищем подкатегории в: {main_category_url}")
        driver.get(main_category_url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Сохраняем HTML для отладки
        debug_file = f"debug_{main_category_url.split('/')[-2]}_{uuid.uuid4().hex[:8]}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info(f"🔍 HTML сохранен в {debug_file}")

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        subcategories = []

        # ДЛЯ СОРНЯКОВ - ищем прямые ссылки на детальные страницы
        if 'sornyaki' in main_category_url:
            logger.info("🌱 Обрабатываем сорняки - ищем прямые ссылки")

            # Из HTML видно, что используется класс .agro-item с ссылкой .title
            agro_items = soup.select('div.agro-item')
            for item in agro_items:
                # Ищем ссылку внутри элемента
                link = item.find('a', class_='title') or item.find('a')
                if link and link.get('href'):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)

                    # Фильтр для ссылок на сорняки
                    if (href.startswith('/harmful/sornyaki/') and
                            not href.endswith('/') and  # НЕ категории
                            len(text) > 3 and
                            not any(exclude in text.lower() for exclude in
                                    ['главная', 'назад', 'меню', 'поиск', 'контакты', 'каталог'])):
                        detail_url = urljoin(BASE_URL, href)
                        subcategories.append({
                            'name': text,
                            'url': detail_url
                        })
                        logger.info(f"🌱 Найден сорняк: {text}")

        # ДЛЯ БОЛЕЗНЕЙ И ВРЕДИТЕЛЕЙ - ищем подкатегории (культуры)
        else:
            logger.info("🦠🐛 Обрабатываем болезни/вредители - ищем культуры")

            # Из HTML видно, что используется класс .agro-item с ссылкой .title
            agro_items = soup.select('div.agro-item')
            for item in agro_items:
                # Ищем ссылку внутри элемента
                link = item.find('a', class_='title') or item.find('a')
                if link and link.get('href'):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)

                    if (href.startswith('/harmful/') and
                            href.endswith('/') and
                            len(text) > 5 and
                            not any(exclude in text.lower() for exclude in
                                    ['главная', 'назад', 'меню', 'поиск', 'контакты'])):

                        subcategory_url = urljoin(BASE_URL, href)
                        if not any(sub['url'] == subcategory_url for sub in subcategories):
                            subcategories.append({
                                'name': text,
                                'url': subcategory_url
                            })
                            logger.info(f"📂 Найдена культура: {text}")

        logger.info(f"✅ Найдено {len(subcategories)} подкатегорий/элементов")
        return subcategories

    except Exception as e:
        logger.error(f"❌ Ошибка получения подкатегорий: {e}")
        return []
    finally:
        driver.quit()


def get_detail_links_from_culture(culture_url):
    """Получение детальных ссылок из подкатегории культуры"""
    driver = get_webdriver()

    try:
        logger.info(f"🔍 Ищем детальные ссылки в: {culture_url}")
        driver.get(culture_url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Сохраняем HTML для отладки
        debug_file = f"debug_culture_{uuid.uuid4().hex[:8]}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info(f"🔍 HTML культуры сохранен в {debug_file}")

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        detail_links = []

        # Определяем тип (болезни или вредители) из URL
        is_diseases = 'bolezni' in culture_url
        is_pests = 'vrediteli' in culture_url

        # Ищем все agro-item элементы
        agro_items = soup.select('div.agro-item')

        for item in agro_items:
            # Ищем ссылку внутри элемента
            link = item.find('a', class_='title') or item.find('a')
            if link and link.get('href'):
                href = link.get('href', '')
                text = link.get_text(strip=True)

                # Фильтр для детальных страниц
                if (href.startswith('/harmful/') and
                        not href.endswith('/') and  # НЕ категории
                        len(text) > 5 and
                        href != culture_url.replace(BASE_URL, '') and
                        not any(exclude in text.lower() for exclude in
                                ['главная', 'назад', 'меню', 'поиск', 'заказать', 'подробнее', 'контакты'])):

                    # Проверяем, что ссылка соответствует типу
                    if ((is_diseases and 'bolezni' in href) or
                            (is_pests and 'vrediteli' in href)):
                        detail_url = urljoin(BASE_URL, href)
                        detail_links.append({
                            'name': text,
                            'url': detail_url
                        })
                        logger.info(f"📄 Найдена детальная страница: {text}")

        # Удаляем дубликаты
        seen_urls = set()
        unique_links = []
        for link in detail_links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)

        logger.info(f"✅ Найдено {len(unique_links)} детальных ссылок")
        return unique_links

    except Exception as e:
        logger.error(f"❌ Ошибка получения детальных ссылок: {e}")
        return []
    finally:
        driver.quit()


def scrape_detail_page(page_url, category_type):
    """Обработка детальной страницы"""
    driver = get_webdriver()

    try:
        logger.info(f"📄 Обрабатываем: {page_url}")
        driver.get(page_url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Парсим контент
        content = parse_content_from_html(soup)
        if not content or not content['title']:
            logger.warning(f"❌ Не удалось получить контент с {page_url}")
            return None

        logger.info(f"📝 Найден: {content['title']}")

        # Переводы (если есть API ключ)
        translations = {}
        if OPENAI_API_KEY:
            logger.info("🌍 Выполняем переводы...")
            for field in ['description_ru', 'symptoms_ru', 'development_conditions_ru', 'control_measures_ru']:
                if content[field]:
                    translations[field.replace('_ru', '_ua')] = translate_text_gpt(content[field], "ukrainian")
                    translations[field.replace('_ru', '_en')] = translate_text_gpt(content[field], "english")
                    time.sleep(0.5)
                else:
                    translations[field.replace('_ru', '_ua')] = ""
                    translations[field.replace('_ru', '_en')] = ""

            name_en = translate_text_gpt(content['title'], "english")
        else:
            logger.warning("⚠️ API ключ не найден - пропускаем переводы")
            for field in ['description_ua', 'description_en', 'symptoms_ua', 'symptoms_en',
                          'development_conditions_ua', 'development_conditions_en',
                          'control_measures_ua', 'control_measures_en']:
                translations[field] = ""
            name_en = ""

        # Скачиваем изображения
        logger.info("📸 Скачиваем изображения...")
        image_urls = extract_images_from_page(soup, page_url)

        item_id = str(uuid.uuid4())
        downloaded_images = []

        if image_urls:
            for i, image_url in enumerate(image_urls):
                file_extension = '.jpg'
                try:
                    parsed_url = urlparse(image_url)
                    file_extension = os.path.splitext(parsed_url.path)[1] or '.jpg'
                except:
                    pass

                safe_title = "".join(c for c in content['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_title = safe_title.replace(' ', '_')[:30]

                if len(image_urls) == 1:
                    filename = f"{category_type}_{safe_title}_{item_id[:8]}{file_extension}"
                else:
                    filename = f"{category_type}_{safe_title}_{item_id[:8]}_{i + 1:02d}{file_extension}"

                filepath = os.path.join(IMAGES_DIR, category_type, filename)

                if download_image(image_url, filepath, page_url):
                    downloaded_images.append({
                        'image_url': image_url,
                        'image_path': filepath,
                        'filename': filename
                    })

                time.sleep(random.uniform(0.5, 1.5))

        # Определяем культуры
        text_for_crops = (content['description_ru'] + ' ' + content['symptoms_ru']).lower()
        crops = []
        crop_keywords = ['пшеница', 'рожь', 'ячмень', 'овес', 'кукуруза', 'подсолнечник', 'соя', 'рапс', 'свекла',
                         'картофель']

        for crop in crop_keywords:
            if crop in text_for_crops:
                crops.append(crop)

        if not crops:
            crops = ['пшеница']

        # Формируем результат
        result = {
            'id': item_id,
            'name': content['title'],
            'name_en': name_en,
            'scientific_name': content['scientific_name'],
            'description_ru': content['description_ru'],
            'description_ua': translations.get('description_ua', ''),
            'description_en': translations.get('description_en', ''),
            'symptoms_ru': content['symptoms_ru'],
            'symptoms_ua': translations.get('symptoms_ua', ''),
            'symptoms_en': translations.get('symptoms_en', ''),
            'development_conditions_ru': content['development_conditions_ru'],
            'development_conditions_ua': translations.get('development_conditions_ua', ''),
            'development_conditions_en': translations.get('development_conditions_en', ''),
            'control_measures_ru': content['control_measures_ru'],
            'control_measures_ua': translations.get('control_measures_ua', ''),
            'control_measures_en': translations.get('control_measures_en', ''),
            'source_urls': page_url,
            'crops': crops,
            'images': downloaded_images,
            'is_active': True,
            'version': 1
        }

        logger.info(f"✅ Обработано: {content['title']} ({len(downloaded_images)} изображений)")
        return result

    except Exception as e:
        logger.error(f"❌ Ошибка обработки {page_url}: {e}")
        return None
    finally:
        driver.quit()


def save_data_to_csv(data, category_type):
    """Сохранение данных в CSV файлы"""
    if not data:
        logger.warning(f"❌ Нет данных для сохранения в {category_type}")
        return

    logger.info(f"💾 Сохраняем {len(data)} записей для {category_type}")

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

    # 2. Описания
    with open(descriptions_csv, 'w', encoding='utf-8', newline='') as f:
        if category_type == 'diseases':
            fieldnames = [
                'id', 'disease_id', 'description_ru', 'description_ua', 'description_en',
                'symptoms_ru', 'symptoms_ua', 'symptoms_en',
                'development_conditions_ru', 'development_conditions_ua', 'development_conditions_en',
                'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                'photo_path', 'source_urls', 'version'
            ]
        elif category_type == 'pests':
            fieldnames = [
                'id', 'vermin_id', 'description_ru', 'description_ua', 'description_en',
                'damage_symptoms_ru', 'damage_symptoms_ua', 'damage_symptoms_en',
                'biology_ru', 'biology_ua', 'biology_en',
                'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                'photo_path', 'source_urls', 'version'
            ]
        else:  # weeds
            fieldnames = [
                'id', 'weed_id', 'description_ru', 'description_ua', 'description_en',
                'biological_features_ru', 'biological_features_ua', 'biological_features_en',
                'harmfulness_ru', 'harmfulness_ua', 'harmfulness_en',
                'control_measures_ru', 'control_measures_ua', 'control_measures_en',
                'photo_path', 'source_urls', 'version'
            ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
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
                'source_urls': item['source_urls'],
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

    # 3. Изображения
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

    # 4. Культуры
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


def process_category_universal(category_type, max_items=None):
    """УНИВЕРСАЛЬНАЯ обработка категории"""
    logger.info(f"🚀 УНИВЕРСАЛЬНАЯ обработка: {category_type}")

    # URL главных категорий
    main_urls = {
        'diseases': 'https://betaren.ru/harmful/bolezni/',
        'pests': 'https://betaren.ru/harmful/vrediteli/',
        'weeds': 'https://betaren.ru/harmful/sornyaki/'
    }

    main_url = main_urls.get(category_type)
    if not main_url:
        logger.error(f"❌ Неизвестная категория: {category_type}")
        return []

    # Получаем подкатегории или прямые ссылки
    subcategories = get_subcategory_links(main_url)

    if not subcategories:
        logger.error(f"❌ Не найдено подкатегорий для {category_type}")
        return []

    # Собираем все детальные ссылки
    all_detail_links = []

    for subcat in subcategories:
        if category_type == 'weeds':
            # Для сорняков - это уже детальные ссылки
            all_detail_links.append(subcat)
        else:
            # Для болезней и вредителей - получаем детальные ссылки из культур
            detail_links = get_detail_links_from_culture(subcat['url'])
            all_detail_links.extend(detail_links)
            time.sleep(1)

    # Ограничиваем если нужно
    if max_items and len(all_detail_links) > max_items:
        all_detail_links = all_detail_links[:max_items]
        logger.info(f"⚠️ Ограничиваем до {max_items} элементов")

    logger.info(f"📊 Будем обрабатывать {len(all_detail_links)} ссылок для {category_type}")

    # Обрабатываем каждую детальную ссылку
    processed_data = []

    for i, link in enumerate(all_detail_links, 1):
        logger.info(f"📄 [{i}/{len(all_detail_links)}] Обрабатываем: {link['name']}")

        try:
            result = scrape_detail_page(link['url'], category_type)

            if result:
                processed_data.append(result)
                logger.info(f"✅ Успешно: {result['name']}")

                # Промежуточное сохранение каждые 5 элементов
                if len(processed_data) % 5 == 0:
                    save_data_to_csv(processed_data, category_type)
            else:
                logger.warning(f"❌ Не обработано: {link['name']}")

            time.sleep(SLEEP_BETWEEN_REQUESTS)

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            continue

    # Финальное сохранение
    if processed_data:
        save_data_to_csv(processed_data, category_type)
        logger.info(f"🎉 {category_type} завершено! Обработано: {len(processed_data)} элементов")
    else:
        logger.warning(f"❌ Не удалось обработать ни одного элемента для {category_type}")

    return processed_data


def main():
    """Основная функция"""
    print("🔧 УНИВЕРСАЛЬНЫЙ скрапер Betaren.ru")
    print("   ✅ Обходит ВСЕ культуры и подкатегории")
    print("   ✅ Собирает ВСЕ болезни, вредители, сорняки")
    print("   ✅ Скачивает изображения")
    print("   ✅ Создает полные CSV файлы")
    print()
    print("1. БОЛЕЗНИ - полный сбор по всем культурам")
    print("2. ВРЕДИТЕЛИ - полный сбор по всем культурам")
    print("3. СОРНЯКИ - полный сбор")
    print("4. ВСЕ КАТЕГОРИИ - полный сбор")
    print("5. ТЕСТ: по 3 элемента из каждой категории")

    choice = input("\nВыберите опцию (1-5): ").strip()

    if not OPENAI_API_KEY:
        logger.warning("⚠️ OpenAI API ключ не найден - переводы будут пропущены")
        proceed = input("Продолжить без переводов? (y/n): ").strip().lower()
        if proceed != 'y':
            return

    create_directories()

    if choice == "1":
        logger.info("🦠 ПОЛНАЯ обработка БОЛЕЗНЕЙ")
        process_category_universal('diseases')

    elif choice == "2":
        logger.info("🐛 ПОЛНАЯ обработка ВРЕДИТЕЛЕЙ")
        process_category_universal('pests')

    elif choice == "3":
        logger.info("🌱 ПОЛНАЯ обработка СОРНЯКОВ")
        process_category_universal('weeds')

    elif choice == "4":
        logger.info("🚀 ПОЛНАЯ обработка ВСЕХ категорий")
        process_category_universal('diseases')
        process_category_universal('pests')
        process_category_universal('weeds')

    elif choice == "5":
        logger.info("🧪 ТЕСТОВЫЙ режим")
        process_category_universal('diseases', max_items=3)
        process_category_universal('pests', max_items=3)
        process_category_universal('weeds', max_items=3)

    else:
        print("❌ Некорректный выбор")
        return

    print(f"\n🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
    print(f"📁 Результаты в папке: {OUTPUT_DIR}")
    print(f"🖼️ Изображения в папке: {IMAGES_DIR}")


if __name__ == "__main__":
    main()