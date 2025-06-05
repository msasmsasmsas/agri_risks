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
        logging.FileHandler("image_downloader.log", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ImageDownloader")

# Настройки
OUTPUT_DIR = os.getenv('DOWNLOAD_DIR', 'downloads')
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', 'D:/crawler_risks/chromedriver.exe')
IMAGES_DIR = os.path.join(OUTPUT_DIR, 'images')

# Список User-Agent
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.142 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.142 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
]

def create_directories():
    """Создание необходимых директорий"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    for folder in ["diseases", "pests", "weeds", "test", "manual"]:
        os.makedirs(os.path.join(IMAGES_DIR, folder), exist_ok=True)
    logger.info("Директории созданы")

def download_image_requests(url, filepath, referer=None):
    """Скачивание изображения через requests"""
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if referer:
            headers['Referer'] = referer
        
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()
        
        # Проверяем, что это действительно изображение
        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
            logger.warning(f"Неподдерживаемый тип контента: {content_type} для {url}")
            return False
        
        # Записываем файл
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Проверяем размер файла
        if os.path.getsize(filepath) < 1024:  # Менее 1KB
            logger.warning(f"Слишком маленький файл {filepath}, возможно это не изображение")
            os.remove(filepath)
            return False
        
        logger.info(f"Изображение успешно скачано: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при скачивании {url} через requests: {e}")
        return False

def download_image_selenium(url, filepath, referer=None):
    """Скачивание изображения через Selenium"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    service = Service(CHROMEDRIVER_PATH)
    driver = None
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(20)
        
        # Переходим на страницу с рефером, если нужно
        if referer:
            driver.get(referer)
            time.sleep(1)
        
        # Переходим к изображению
        driver.get(url)
        time.sleep(2)
        
        # Проверяем, что изображение загрузилось
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "img"))
            )
        except:
            logger.warning(f"Изображение не найдено на странице {url}")
        
        # Убедимся, что директория существует
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Исправляем расширение для скриншота
        screenshot_path = filepath
        if not filepath.lower().endswith('.png'):
            screenshot_path = os.path.splitext(filepath)[0] + '.png'
        
        # Делаем скриншот страницы
        driver.save_screenshot(screenshot_path)
        
        # Если файл создан с .png расширением, но нужен другой формат - переименовываем
        if screenshot_path != filepath and os.path.exists(screenshot_path):
            os.rename(screenshot_path, filepath)
        
        final_path = filepath if os.path.exists(filepath) else screenshot_path
        
        # Проверяем размер файла
        if os.path.getsize(final_path) < 1024:
            logger.warning(f"Слишком маленький файл {final_path}")
            os.remove(final_path)
            return False
        
        logger.info(f"Изображение скачано через Selenium: {final_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при скачивании {url} через Selenium: {e}")
        return False
    finally:
        if driver:
            driver.quit()

def extract_all_images_from_page(page_url):
    """Извлечение всех URL изображений со страницы рисков"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    
    service = Service(CHROMEDRIVER_PATH)
    driver = None
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(20)
        driver.get(page_url)
        
        # Ждем загрузки страницы
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        image_urls = []
        
        # Основные изображения в блоке harmful-detail__picture
        main_picture_block = soup.find('div', class_='harmful-detail__picture')
        if main_picture_block:
            main_img = main_picture_block.find('img', class_='gallery__img')
            if main_img and main_img.has_attr('src'):
                img_src = main_img['src']
                if not any(exclude in img_src.lower() for exclude in ['logo', 'icon', 'company-logo', 'favicon']):
                    image_url = urljoin(page_url, img_src)
                    image_urls.append(image_url)
                    logger.info(f"Найдено основное изображение: {image_url}")
        
        # Галерея изображений в harmful-detail__picture-gallery
        gallery_block = soup.find('div', class_='harmful-detail__picture-gallery')
        if gallery_block:
            # Ищем все изображения в галерее
            gallery_images = gallery_block.find_all('img', class_='gallery__img')
            for img in gallery_images:
                if img.has_attr('src'):
                    img_src = img['src']
                    if not any(exclude in img_src.lower() for exclude in ['logo', 'icon', 'company-logo', 'favicon']):
                        image_url = urljoin(page_url, img_src)
                        if image_url not in image_urls:  # Избегаем дублирования
                            image_urls.append(image_url)
                            logger.info(f"Найдено изображение галереи: {image_url}")
            
            # Также проверяем ссылки на полноразмерные изображения
            gallery_links = gallery_block.find_all('a', class_='gallery__link')
            for link in gallery_links:
                if link.has_attr('href'):
                    href = link['href']
                    if any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        image_url = urljoin(page_url, href)
                        if image_url not in image_urls:
                            image_urls.append(image_url)
                            logger.info(f"Найдена ссылка на полноразмерное изображение: {image_url}")
        
        # Дополнительный поиск в swiper-slider (если есть слайдер)
        slider_block = soup.find('div', class_='swiper-slide')
        if slider_block:
            slider_images = soup.find_all('div', class_='swiper-slide')
            for slide in slider_images:
                img = slide.find('img', class_='gallery__img')
                if img and img.has_attr('src'):
                    img_src = img['src']
                    if not any(exclude in img_src.lower() for exclude in ['logo', 'icon', 'company-logo', 'favicon']):
                        image_url = urljoin(page_url, img_src)
                        if image_url not in image_urls:
                            image_urls.append(image_url)
                            logger.info(f"Найдено изображение слайдера: {image_url}")
        
        # Поиск в других возможных местах
        other_selectors = [
            'div.gallery img',
            'article img[src*="upload"]',
            'main img[src*="upload"]',
            '.harmful-image img',
            '.content img[src*="upload"]'
        ]
        
        for selector in other_selectors:
            images = soup.select(selector)
            for img in images:
                if img.has_attr('src'):
                    img_src = img['src']
                    if not any(exclude in img_src.lower() for exclude in ['logo', 'icon', 'company-logo', 'favicon']):
                        image_url = urljoin(page_url, img_src)
                        if image_url not in image_urls:
                            image_urls.append(image_url)
                            logger.info(f"Найдено дополнительное изображение: {image_url}")
        
        logger.info(f"Всего найдено {len(image_urls)} уникальных изображений на {page_url}")
        return image_urls
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении изображений со страницы {page_url}: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def download_direct_image(image_url, folder, filename, referer=None):
    """Прямое скачивание изображения по URL"""
    if not image_url:
        logger.warning("Пустой URL изображения")
        return ''
    
    # Создаем папку, если её нет
    folder_path = os.path.join(IMAGES_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)
    
    # Создаем полный путь
    filepath = os.path.join(folder_path, filename)
    
    # Проверяем, не скачан ли уже файл
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
        logger.info(f"Файл уже существует: {filepath}")
        return filepath
    
    logger.info(f"Прямое скачивание изображения: {image_url}")
    
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if referer:
            headers['Referer'] = referer
        
        response = requests.get(image_url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()
        
        # Записываем файл
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Проверяем размер файла
        if os.path.getsize(filepath) < 1024:
            logger.warning(f"Слишком маленький файл {filepath}")
            os.remove(filepath)
            return ''
        
        logger.info(f"Изображение успешно скачано: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Ошибка при прямом скачивании {image_url}: {e}")
        return ''
    """Основная функция скачивания изображения"""
    if not url:
        logger.warning("Пустой URL изображения")
        return ''
    
    # Создаем папку, если её нет
    folder_path = os.path.join(IMAGES_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)
    
    # Создаем полный путь
    filepath = os.path.join(folder_path, filename)
    
    # Проверяем, не скачан ли уже файл
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
        logger.info(f"Файл уже существует: {filepath}")
        return filepath
    
    logger.info(f"Скачиваем изображение: {url}")
    
    # Пробуем через requests
    if download_image_requests(url, filepath, referer):
        return filepath
    
    # Если не получилось, пробуем через Selenium
    logger.info(f"Пробуем скачать через Selenium: {url}")
    if download_image_selenium(url, filepath, referer):
        return filepath
    
    logger.error(f"Не удалось скачать изображение: {url}")
    return ''

def process_csv_file(csv_file, url_column, id_column, type_name):
    """Обработка CSV файла и скачивание всех изображений с каждой страницы"""
    if not os.path.exists(csv_file):
        logger.error(f"Файл {csv_file} не найден")
        return
    
    logger.info(f"Обрабатываем файл: {csv_file}")
    
    downloaded_count = 0
    failed_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if url_column not in row or id_column not in row:
                    logger.warning(f"Отсутствуют необходимые колонки в строке: {row}")
                    continue
                
                page_url = row[url_column].strip()
                item_id = row[id_column].strip()
                
                if not page_url or not item_id:
                    logger.warning(f"Пустые значения URL или ID: {page_url}, {item_id}")
                    continue
                
                # Скачиваем все изображения со страницы
                logger.info(f"Обрабатываем страницу: {page_url}")
                downloaded_files = download_multiple_images(page_url, type_name, f"{type_name}_{item_id}")
                
                if downloaded_files:
                    downloaded_count += len(downloaded_files)
                    logger.info(f"Успешно скачано {len(downloaded_files)} изображений для {item_id}")
                else:
                    failed_count += 1
                    logger.error(f"Не удалось скачать изображения для {item_id}")
                
                # Пауза между обработкой страниц
                time.sleep(random.uniform(2, 4))
    
    except Exception as e:
        logger.error(f"Ошибка при обработке файла {csv_file}: {e}")
    
    logger.info(f"Обработка {csv_file} завершена. Скачано изображений: {downloaded_count}, Неудачных страниц: {failed_count}")

def download_from_json_descriptions():
    """Скачивание изображений из JSON файлов с описаниями"""
    json_files = [
        ('disease_descriptions.csv', 'source_urls', 'disease_id', 'diseases'),
        ('vermin_descriptions.csv', 'source_urls', 'vermin_id', 'pests'),
        ('weed_descriptions.csv', 'source_urls', 'weed_id', 'weeds')
    ]
    
    for csv_file, url_col, id_col, folder in json_files:
        csv_path = os.path.join(OUTPUT_DIR, csv_file)
        process_csv_file(csv_path, url_col, id_col, folder)

def download_multiple_images(page_url, output_folder="manual", base_filename=None):
    """Скачивание всех изображений с одной страницы рисков"""
    if not base_filename:
        base_filename = f"risk_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Скачиваем все изображения со страницы: {page_url}")
    
    # Извлекаем все URL изображений
    image_urls = extract_all_images_from_page(page_url)
    
    if not image_urls:
        logger.error("Не найдены изображения на странице")
        return []
    
    downloaded_files = []
    
    for i, image_url in enumerate(image_urls):
        # Определяем расширение файла
        parsed_url = urlparse(image_url)
        file_extension = os.path.splitext(parsed_url.path)[1] or '.jpg'
        
        # Создаем уникальное имя файла
        if len(image_urls) == 1:
            filename = f"{base_filename}{file_extension}"
        else:
            filename = f"{base_filename}_{i+1:02d}{file_extension}"
        
        # Скачиваем изображение
        result_path = download_direct_image(image_url, output_folder, filename, page_url)
        
        if result_path:
            downloaded_files.append(result_path)
            logger.info(f"Успешно скачано: {filename}")
        else:
            logger.error(f"Не удалось скачать: {filename}")
        
        # Пауза между скачиваниями
        time.sleep(random.uniform(0.5, 1.5))
    
    logger.info(f"Скачано {len(downloaded_files)} из {len(image_urls)} изображений")
    return downloaded_files
def download_single_image(page_url, output_folder="manual", filename=None):
    """Скачивание первого найденного изображения со страницы (для обратной совместимости)"""
    if not filename:
        filename = f"image_{uuid.uuid4().hex[:8]}.jpg"
    
    logger.info(f"Скачиваем первое изображение со страницы: {page_url}")
    
    # Извлекаем все URL изображений
    image_urls = extract_all_images_from_page(page_url)
    
    if image_urls:
        # Берем первое изображение
        image_url = image_urls[0]
        result_path = download_direct_image(image_url, output_folder, filename, page_url)
        if result_path:
            logger.info(f"Изображение успешно скачано: {result_path}")
            return result_path
        else:
            logger.error("Не удалось скачать изображение")
            return None
    else:
        logger.error("Не найдены изображения на странице")
        return None

def main():
    """Основная функция"""
    print("Модуль для скачивания изображений с сайта Betaren")
    print("1. Скачать все изображения из CSV файлов")
    print("2. Скачать одно изображение по URL страницы")
    print("3. Тестовое скачивание с конкретной страницы")
    print("4. Прямое скачивание изображения по URL")
    print("5. Скачать ВСЕ изображения с одной страницы рисков")
    
    choice = input("Выберите опцию (1-5): ").strip()
    
    create_directories()
    
    if choice == "1":
        logger.info("Начинаем массовое скачивание всех изображений...")
        download_from_json_descriptions()
        logger.info("Массовое скачивание завершено!")
    
    elif choice == "2":
        page_url = input("Введите URL страницы: ").strip()
        if page_url:
            result = download_single_image(page_url)
            if result:
                print(f"Изображение сохранено: {result}")
            else:
                print("Не удалось скачать изображение")
        else:
            print("Некорректный URL")
    
    elif choice == "3":
        # Тестовая страница
        test_url = "https://betaren.ru/harmful/bolezni/bolezni-zernovykh-kultur/gelmintosporioznaya_gnil/"
        logger.info(f"Тестируем скачивание с: {test_url}")
        result = download_single_image(test_url, "test", "test_disease.jpg")
        if result:
            print(f"Тестовое изображение сохранено: {result}")
        else:
            print("Тестовое скачивание не удалось")
    
    elif choice == "4":
        image_url = input("Введите прямой URL изображения: ").strip()
        if image_url:
            filename = input("Введите имя файла (или нажмите Enter для автогенерации): ").strip()
            if not filename:
                filename = f"direct_image_{uuid.uuid4().hex[:8]}.jpg"
            
            result = download_direct_image(image_url, "manual", filename)
            if result:
                print(f"Изображение сохранено: {result}")
            else:
                print("Не удалось скачать изображение")
        else:
            print("Некорректный URL")
    
    elif choice == "5":
        page_url = input("Введите URL страницы с рисками: ").strip()
        if page_url:
            base_name = input("Введите базовое имя файлов (или нажмите Enter для автогенерации): ").strip()
            if not base_name:
                base_name = f"risk_images_{uuid.uuid4().hex[:8]}"
            
            results = download_multiple_images(page_url, "manual", base_name)
            if results:
                print(f"Скачано {len(results)} изображений:")
                for img_path in results:
                    print(f" - {img_path}")
            else:
                print("Не удалось скачать изображения")
        else:
            print("Некорректный URL")
    
    else:
        print("Некорректный выбор")

if __name__ == "__main__":
    main()