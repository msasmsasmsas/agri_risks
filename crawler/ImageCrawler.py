"""
Module for collecting images of agricultural crops and their diseases.
Uses data from CSV files to form search queries and download images.
"""

import os
import csv
import time
import logging
import urllib.request
import urllib.parse
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import hashlib
import re
import random
import uuid
from bs4 import BeautifulSoup
import requests
import urllib.parse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("image_crawler")

# Настройка кодировки консоли для корректного отображения кириллицы
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Константы
# Используем абсолютный путь относительно расположения скрипта
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = BASE_DIR / "crawler" / "csv_output"
DOWNLOAD_DIR = BASE_DIR / "crawler" / "download" / "images"  # Исправлено согласно ТЗ
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

# Functions for working with CSV
def get_csv_files() -> List[Path]:
    """Gets a list of all CSV files from the directory."""
    if not CSV_DIR.exists():
        logger.error(f"Директория {CSV_DIR.absolute()} не существует")
        return []

    files = list(CSV_DIR.glob("*.csv"))
    if not files:
        logger.warning(f"В директории {CSV_DIR.absolute()} не найдено CSV-файлов")
    else:
        logger.info(f"Найдено {len(files)} CSV-файлов в {CSV_DIR.absolute()}")

    return files

def read_csv_data(file_path: Path) -> List[Dict]:
    """Reads data from a CSV file."""
    data = []
    try:
        if not file_path.exists():
            logger.error(f"Файл {file_path.absolute()} не существует")
            return []

        logger.info(f"Чтение файла: {file_path.absolute()}")
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)

        logger.info(f"Успешно прочитано {len(data)} строк из файла {file_path.name}")
        return data
    except UnicodeDecodeError:
        logger.error(f"Ошибка кодировки файла {file_path}. Попытка чтения с другой кодировкой...")
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            logger.info(f"Успешно прочитано {len(data)} строк из файла {file_path.name} с кодировкой latin-1")
            return data
        except Exception as e:
            logger.error(f"Не удалось прочитать файл {file_path} с альтернативной кодировкой: {e}")
            return []
    except Exception as e:
        logger.error(f"Ошибка чтения файла {file_path}: {e}")
        return []

def extract_culture_risk_info(file_path: Path) -> Tuple[str, str, str]:
    """
    Extracts information about the crop and risk type from the filename.

    Supported formats:
    - diseases_пшеница_cereals.csv -> ("пшеница", "cereals", "diseases")
    - pests_кукуруза_corn.csv -> ("кукуруза", "corn", "pests")
    - example_diseases_wheat_cereals.csv -> ("wheat", "cereals", "diseases")
    - example_pests_wheat_cereals.csv -> ("wheat", "cereals", "pests")
    """
    file_name = file_path.stem
    parts = file_name.split('_')

    # Check format example_diseases_wheat_cereals.csv
    if len(parts) >= 4 and parts[0] == 'example':
        risk_type = parts[1]  # diseases or pests
        culture_ru = parts[2]  # crop name (wheat)
        culture_en = parts[3]  # crop type (cereals)
        return culture_ru, culture_en, risk_type
    # Check format diseases_пшеница_cereals.csv
    elif len(parts) >= 3:
        risk_type = parts[0]  # diseases or pests
        culture_ru = parts[1]  # name in Russian
        culture_en = parts[2]  # name in English
        return culture_ru, culture_en, risk_type
    else:
        # If the filename format doesn't match expected
        logger.warning(f"Failed to extract information from filename: {file_name}")
        return "unknown", "unknown", "unknown"

# Functions for downloading images
def create_search_query(risk_name: str, culture: str, risk_type: str, search_engine: str = "google") -> str:
    """Creates a search query for images.
import os
import requests
import time
import re
import random
import shutil
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ImageCrawler:
    def __init__(self, base_dir="D:/crawler/download/images", timeout=10, download_limit=30):
        self.base_dir = base_dir
        self.timeout = timeout
        self.download_limit = download_limit
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')

        # Поисковые движки для разных языков
        self.search_engines = [
            'https://www.google.com/search?q={}&tbm=isch',
            'https://yandex.ru/images/search?text={}',
            'https://www.bing.com/images/search?q={}',
            'https://duckduckgo.com/?q={}&ia=images&iax=images'
        ]

        # Создаем директорию weeds, если она не существует
        if not os.path.exists(os.path.join(self.base_dir, 'weeds')):
            os.makedirs(os.path.join(self.base_dir, 'weeds'))
            print(f"Создана папка {os.path.join(self.base_dir, 'weeds')}")

    def get_translation_pairs(self, term):
        """Создает пары запросов на русском и английском языках"""
        translations = {
            # Болезни сахарной свеклы
            'бурая_гниль': ['brown rot sugar beet', 'бурая гниль сахарной свеклы', 'rhizoctonia root rot sugar beet'],

            # Болезни гороха
            'антракноз_гороха': ['pea anthracnose', 'антракноз гороха', 'colletotrichum pisi'],
            'аскохитоз_гороха': ['ascochyta blight pea', 'аскохитоз гороха', 'mycosphaerella pinodes'],

            # Вредители льна
            'льняная_блошка': ['flax flea beetle', 'льняная блошка', 'longitarsus parvulus'],
            'совка_гамма': ['silver y moth flax', 'совка-гамма на льне', 'autographa gamma'],

            # Вредители зерновых
            'хлебный_жук': ['cereal leaf beetle', 'хлебный жук', 'zabrus tenebrioides'],
            'злаковая_муха': ['frit fly', 'шведская муха', 'oscinella frit'],

            # Сорняки
            'амброзия': ['common ragweed', 'амброзия полыннолистная', 'ambrosia artemisiifolia'],
            'осот_полевой': ['field thistle', 'осот полевой', 'sonchus arvensis'],
            'пырей_ползучий': ['couch grass', 'пырей ползучий', 'elymus repens'],
            'вьюнок_полевой': ['field bindweed', 'вьюнок полевой', 'convolvulus arvensis'],
            'щирица': ['redroot pigweed', 'щирица запрокинутая', 'amaranthus retroflexus']
        }

        # Если для данного термина нет перевода, используем сам термин
        if term not in translations:
            return [term, term]

        return translations[term]

    def create_search_query(self, term, category, crop=None):
        """Создает поисковые запросы для разных категорий"""
        query_templates = {
            'diseases': [
                '{} disease {}',
                '{} symptoms {}',
                '{} pathogen {}',
                '{} infection {}'
            ],
            'pests': [
                '{} pest {}',
                '{} insect {}',
                '{} damage {}',
                '{} larvae {}'
            ],
            'weeds': [
                '{} weed',
                '{} weed identification',
                '{} in field',
                '{} invasive plant'
            ]
        }

        # Получаем переводы для термина
        term_translations = self.get_translation_pairs(term)

        queries = []

        for translation in term_translations:
            if category == 'weeds':
                for template in query_templates[category]:
                    queries.append(template.format(translation))
            else:
                for template in query_templates[category]:
                    if crop:
                        queries.append(template.format(translation, crop))
                    else:
                        queries.append(template.format(translation, ''))

        return queries

    def fetch_image_urls(self, query, engine_index=0, max_links=100):
        """Получает URLs изображений из поисковых систем"""
        image_urls = set()
        search_url = self.search_engines[engine_index].format(quote(query))

        # Используем Selenium для получения динамического контента
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(search_url)

            # Прокручиваем страницу для загрузки большего количества изображений
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            # Ищем элементы изображений в зависимости от поисковой системы
            if engine_index == 0:  # Google
                images = driver.find_elements(By.CSS_SELECTOR, 'img.rg_i')
                for img in images:
                    try:
                        img.click()
                        time.sleep(1)
                        actual_images = driver.find_elements(By.CSS_SELECTOR, '.n3VNCb')
                        for actual_image in actual_images:
                            if actual_image.get_attribute('src') and 'http' in actual_image.get_attribute('src'):
                                image_urls.add(actual_image.get_attribute('src'))
                    except:
                        continue
            elif engine_index == 1:  # Yandex
                images = driver.find_elements(By.CSS_SELECTOR, '.serp-item__thumb')
                for img in images:
                    try:
                        img.click()
                        time.sleep(1)
                        actual_image = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '.MMImage-Origin'))
                        )
                        if actual_image.get_attribute('src'):
                            image_urls.add(actual_image.get_attribute('src'))
                    except:
                        continue
            else:  # Bing и DuckDuckGo
                images = driver.find_elements(By.CSS_SELECTOR, 'img.mimg, img.tile--img')
                for img in images:
                    if img.get_attribute('src') and 'http' in img.get_attribute('src'):
                        image_urls.add(img.get_attribute('src'))

        except Exception as e:
            print(f"Ошибка при получении URL изображений: {e}")
        finally:
            driver.quit()

        return list(image_urls)[:max_links]

    def download_image(self, url, save_path):
        """Загружает изображение по URL и сохраняет его"""
        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=self.timeout)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
                return True
            return False
        except Exception as e:
            print(f"Ошибка при загрузке изображения {url}: {e}")
            return False

    def process_category(self, category, subcategories):
        """Обрабатывает категорию и загружает изображения для всех подкатегорий"""
        category_dir = os.path.join(self.base_dir, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

        for crop, terms in subcategories.items():
            crop_dir = os.path.join(category_dir, crop)
            if not os.path.exists(crop_dir):
                os.makedirs(crop_dir)

            for term in terms:
                term_dir = os.path.join(crop_dir, term)
                # Удаляем папку 'заказать' если она существует
                order_dir = os.path.join(crop_dir, 'заказать')
                if os.path.exists(order_dir):
                    shutil.rmtree(order_dir)
                    print(f"Удалена папка {order_dir}")

                if not os.path.exists(term_dir):
                    os.makedirs(term_dir)

                # Если папка пуста или содержит менее 5 изображений, заполняем ее
                image_count = len([f for f in os.listdir(term_dir) if os.path.isfile(os.path.join(term_dir, f))])
                if image_count < 5:
                    print(f"Загрузка изображений для {term} ({crop}) в категории {category}...")
                    self.download_images_for_term(term, category, crop, term_dir)
                else:
                    print(f"В папке {term_dir} уже есть {image_count} изображений. Пропускаем.")

    def download_images_for_term(self, term, category, crop, save_dir):
        """Загружает изображения для конкретного термина"""
        # Создаем поисковые запросы для термина
        queries = self.create_search_query(term, category, crop)

        # Ограничиваем количество запросов для ускорения
        if len(queries) > 3:
            queries = queries[:3]

        # Счетчик загруженных изображений
        downloaded_count = 0

        for query in queries:
            # Используем разные поисковые системы для каждого запроса
            for engine_index in range(len(self.search_engines)):
                print(f"Поиск в {self.search_engines[engine_index].split('/')[2]} по запросу: {query}")

                # Получаем URLs изображений
                image_urls = self.fetch_image_urls(query, engine_index)

                # Загружаем изображения
                for i, url in enumerate(image_urls):
                    if downloaded_count >= self.download_limit:
                        print(f"Достигнут лимит загрузки ({self.download_limit}) для {term}")
                        return

                    # Формируем имя файла
                    file_extension = os.path.splitext(urlparse(url).path)[1]
                    if not file_extension or file_extension.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
                        file_extension = '.jpg'

                    filename = f"{term}_{engine_index}_{i}{file_extension}"
                    save_path = os.path.join(save_dir, filename)

                    # Загружаем изображение
                    if self.download_image(url, save_path):
                        downloaded_count += 1
                        print(f"Загружено {downloaded_count}/{self.download_limit} изображений для {term}")

                    # Пауза между запросами, чтобы не нагружать сервер
                    time.sleep(random.uniform(0.5, 1.5))

                # Если загрузили достаточно изображений с одного поисковика, переходим к следующему
                if downloaded_count >= self.download_limit // len(self.search_engines):
                    break

    def run(self):
        """Запускает процесс сканирования и загрузки изображений"""
        # Определяем структуру категорий и подкатегорий
        categories = {
            'diseases': {
                'sugar': ['бурая_гниль', 'церкоспороз', 'мучнистая_роса'],
                'pea': ['антракноз_гороха', 'аскохитоз_гороха', 'ржавчина_гороха']
            },
            'pests': {
                'flax': ['льняная_блошка', 'совка_гамма', 'льняной_трипс'],
                'cereals': ['хлебный_жук', 'злаковая_муха', 'хлебная_жужелица']
            },
            'weeds': {
                'common': ['амброзия', 'осот_полевой', 'пырей_ползучий', 'вьюнок_полевой', 'щирица']
            }
        }

        # Обрабатываем каждую категорию
        for category, subcategories in categories.items():
            self.process_category(category, subcategories)

        print("Процесс загрузки изображений завершен.")

# Запуск краулера
if __name__ == "__main__":
    crawler = ImageCrawler()
    crawler.run()
    Args:
        risk_name: Name of the risk (disease or pest)
        culture: Crop name
        risk_type: Type of risk ("diseases" or "pests")
        search_engine: Search engine to use ("google" or "yandex")

    Returns:
        Search query string
    """
    if search_engine.lower() == "yandex":
        # Для Яндекса можно использовать более специфичные запросы
        if risk_type == "diseases":
            return f"{risk_name} болезнь {culture} фото высокое качество"
        else:  # pests
            return f"{risk_name} вредитель {culture} фото макро"
    else:  # google и другие
        if risk_type == "diseases":
            return f"{risk_name} болезнь {culture} фото"
        else:  # pests
            return f"{risk_name} вредитель {culture} фото"

def get_google_image_urls(query: str, max_images: int = 500) -> List[str]:
    """
    Gets image URLs from Google Images for a given query.

    Args:
        query: Search query
        max_images: Maximum number of images to download

    Returns:
        List of image URLs
    """
    query_encoded = urllib.parse.quote(query)
    search_url = f"https://www.google.com/search?q={query_encoded}&tbm=isch&tbs=isz:l"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "TE": "trailers"
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение URL изображений из HTML
        image_urls = []
        
        # Регулярное выражение для поиска URL изображений
        pattern = r'https://[^"\']+\.(?:jpg|jpeg|png|webp)'
        found_urls = re.findall(pattern, response.text)
        
        # Фильтрация URL, чтобы получить только изображения
        for url in found_urls:
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                image_urls.append(url)
                if len(image_urls) >= max_images:
                    break
        
        return image_urls
    except Exception as e:
        logger.error(f"Ошибка при получении изображений из Google: {e}")
        return []

def download_image(url: str, save_path: Path) -> bool:
    """
    Downloads an image by URL and saves it to the specified path.

    Args:
        url: Image URL
        save_path: Path to save the image

    Returns:
        True if download is successful, otherwise False
    """
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if not content_type.startswith('image/'):
                        logger.warning(f"Пропуск URL {url}: не изображение (Content-Type: {content_type})")
                        return False

                    # Determine the file extension based on content type
                    extension = 'jpg'  # Default extension
                    if 'image/jpeg' in content_type.lower():
                        extension = 'jpg'
                    elif 'image/png' in content_type.lower():
                        extension = 'png'
                    elif 'image/webp' in content_type.lower():
                        extension = 'webp'
                    elif 'image/gif' in content_type.lower():
                        extension = 'gif'

                    # Update file path if needed
                    if not str(save_path).lower().endswith(f'.{extension}'):
                        save_path = Path(str(save_path).rsplit('.', 1)[0] + f'.{extension}')

                    try:
                        with open(save_path, 'wb') as out_file:
                            image_data = response.read()
                            if len(image_data) < 1000:  # Проверка минимального размера файла
                                logger.warning(f"Пропуск URL {url}: подозрительно маленький размер ({len(image_data)} байт)")
                                return False
                            out_file.write(image_data)
                        logger.info(f"Загружено изображение: {url} -> {save_path}")
                        return True
                    except (IOError, OSError) as e:
                        logger.error(f"Ошибка записи файла {save_path}: {e}")
                        return False
                else:
                    logger.warning(f"Ошибка HTTP-статуса при загрузке {url}: {response.status}")
                    return False
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP ошибка при загрузке {url}: {e.code} {e.reason}")
            return False
        except urllib.error.URLError as e:
            logger.error(f"URL ошибка при загрузке {url}: {e.reason}")
            return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке {url}: {e}")
        return False

def process_risk_item(item: Dict, culture_ru: str, culture_en: str, risk_type: str, search_engine: str = 'google', max_images: int = 500) -> None:
    """
    Processes one risk item (disease or pest).

    Args:
        item: Dictionary with risk data
        culture_ru: Crop name in Russian
        culture_en: Crop name in English
        risk_type: Risk type (diseases or pests)
        search_engine: Search engine to use ('google', 'yandex', or 'both')
        max_images: Maximum number of images to download per risk
    """
    try:
        # Get risk name (pest or disease name)
        risk_name_ru = item.get('name', '').strip()
        risk_name_en = item.get('english_name', '').strip()

        if not risk_name_ru:
            logger.warning(f"Пропуск элемента без имени: {item}")
            return

        # If English name is missing, create it from Russian using transliteration
        if not risk_name_en:
            # Простая транслитерация с заменой пробелов на подчеркивания и приведением к нижнему регистру
            import re
            # Удаляем все символы кроме букв, цифр, пробелов и подчеркиваний
            risk_name_ru_clean = re.sub(r'[^\w\s]', '', risk_name_ru)
            risk_name_en = risk_name_ru_clean.replace(' ', '_').lower()
            logger.warning(f"Английское имя не найдено для '{risk_name_ru}', используем транслитерацию: '{risk_name_en}'")

        # Создаем директорию для сохранения изображений
        # Используем английское имя риска для пути согласно требованиям ТЗ
        try:
            risk_dir = DOWNLOAD_DIR / risk_type / culture_en / risk_name_en.replace(' ', '_').lower()
            risk_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Используется директория для сохранения: {risk_dir}")
        except (OSError, IOError) as e:
            logger.error(f"Не удалось создать директорию для {risk_name_ru}: {e}")
            return

        # Check if we need to download images
        try:
            existing_images = list(risk_dir.glob('*'))
            if len(existing_images) >= max_images:
                logger.info(f"Уже имеется {len(existing_images)} изображений для {risk_name_en}, пропускаем")
                return
        except Exception as e:
            logger.error(f"Ошибка при проверке существующих изображений для {risk_name_en}: {e}")
            existing_images = []

        # Create search query and get image URLs based on selected search engine
        query = create_search_query(risk_name_ru, culture_ru, risk_type, search_engine)
        logger.info(f"Поиск изображений для: {query} с использованием {search_engine}")

        # Get image URLs based on search engine
        image_urls = []
        if search_engine.lower() == 'google':
            image_urls = get_google_image_urls(query, max_images=max_images)
        elif search_engine.lower() == 'yandex':
            try:
                import yandex_crawler
                image_urls = yandex_crawler.get_yandex_image_urls(query, max_images=max_images)
            except ImportError:
                logger.error("Модуль yandex_crawler не найден, используем Google")
                image_urls = get_google_image_urls(query, max_images=max_images)
        elif search_engine.lower() == 'both':
            try:
                import yandex_crawler
                # Получаем изображения из обоих источников и объединяем результаты
                yandex_urls = yandex_crawler.get_yandex_image_urls(query, max_images=max_images//2)
                google_urls = get_google_image_urls(query, max_images=max_images//2)
                # Объединяем результаты, чередуя источники для разнообразия
                image_urls = []
                for i in range(max(len(yandex_urls), len(google_urls))):
                    if i < len(yandex_urls):
                        image_urls.append(yandex_urls[i])
                    if i < len(google_urls):
                        image_urls.append(google_urls[i])
                # Ограничиваем количество URL до максимального
                image_urls = image_urls[:max_images]
            except ImportError:
                logger.error("Модуль yandex_crawler не найден, используем только Google")
                image_urls = get_google_image_urls(query, max_images=max_images)
        else:  # По умолчанию используем Google
            image_urls = get_google_image_urls(query, max_images=max_images)

        if not image_urls:
            logger.warning(f"Не удалось найти изображения для запроса: {query}")
            # Попробуем альтернативный запрос без указания типа риска
            alt_query = f"{risk_name_ru} {culture_ru} фото"
            logger.info(f"Пробуем альтернативный запрос: {alt_query}")

            if search_engine.lower() == 'yandex':
                try:
                    import yandex_crawler
                    image_urls = yandex_crawler.get_yandex_image_urls(alt_query, max_images=max_images)
                except ImportError:
                    image_urls = get_google_image_urls(alt_query, max_images=max_images)
            else:
                image_urls = get_google_image_urls(alt_query, max_images=max_images)

            if not image_urls:
                logger.error(f"Не удалось найти изображения даже с альтернативным запросом: {alt_query}")
                return

        # Download images
        downloads_count = 0
        for i, url in enumerate(image_urls):
            if len(existing_images) + downloads_count >= max_images:
                logger.info(f"Достигнут предел в {max_images} изображений для {risk_name_en}")
                break

            try:
                # Create filename based on required pattern: risk_type_culture_guid_number.jpg
                # Extract GUID from item or generate one based on risk name to ensure consistency
                # Use the same GUID for all images of the same risk/disease
                if 'guid' in item:
                    guid = item['guid']
                else:
                    # Generate deterministic GUID based on risk name and culture to ensure all photos 
                    # of the same disease have the same GUID
                    guid_seed = f"{risk_type}_{culture_en}_{risk_name_en}".lower()
                    guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, guid_seed))

                # Format filename according to the required pattern
                file_number = i + len(existing_images) + 1
                file_ext = os.path.splitext(url)[1]
                if not file_ext or file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
                    file_ext = '.jpg'

                save_path = risk_dir / f"{risk_type}_{culture_en.lower()}_{guid}_{file_number:02d}{file_ext}"

                # Skip if file already exists
                if save_path.exists():
                    logger.debug(f"Файл {save_path} уже существует, пропускаем")
                    continue

                # Download image
                if download_image(url, save_path):
                    downloads_count += 1

                # Small delay to avoid blocking
                time.sleep(random.uniform(1.0, 3.0))
            except Exception as e:
                logger.error(f"Ошибка при обработке URL {url} для {risk_name_ru}: {e}")
                continue

        logger.info(f"Загружено {downloads_count} новых изображений для {risk_name_ru}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при обработке риска: {e}")
        return

def process_csv_file(file_path: Path, search_engine: str = 'google', max_images: int = 10, delay: float = 2.0) -> None:
    """
    Processes one CSV file, extracting risk data and downloading images.

    Args:
        file_path: Path to CSV file
        search_engine: Search engine to use ('google', 'yandex', or 'both')
        max_images: Maximum number of images to download per risk
        delay: Delay between processing items in seconds
    """
    logger.info(f"Обработка файла: {file_path}")

    # Extract information about crop and risk type from filename
    culture_ru, culture_en, risk_type = extract_culture_risk_info(file_path)
    logger.info(f"Извлечена информация о культуре: {culture_ru} ({culture_en}), тип риска: {risk_type}")

    # Read data from CSV
    data = read_csv_data(file_path)
    logger.info(f"Найдено {len(data)} элементов в {file_path}")

    # Process each risk item
    successful_items = 0
    for i, item in enumerate(data):
        logger.info(f"Обработка элемента {i+1}/{len(data)}")
        try:
            # Передаем дополнительные параметры в process_risk_item
            process_risk_item(
                item, 
                culture_ru, 
                culture_en, 
                risk_type, 
                search_engine=search_engine,
                max_images=max_images
            )
            successful_items += 1
        except Exception as e:
            logger.error(f"Ошибка при обработке элемента {item.get('name', 'неизвестно')}: {e}")

        # Small delay between processing items
        delay_time = random.uniform(delay * 0.8, delay * 1.2)
        logger.debug(f"Пауза между запросами: {delay_time:.2f} секунд")
        time.sleep(delay_time)

    logger.info(f"Успешно обработано {successful_items} из {len(data)} элементов в файле {file_path.name}")

def main():
    """Main function to start the crawler."""
    import argparse

    # Создаем парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Crawler for downloading images of agricultural risks.')
    parser.add_argument('--engine', type=str, choices=['google', 'yandex', 'both'], default='google',
                        help='Search engine to use: google, yandex or both (default: google)')
    parser.add_argument('--max-images', type=int, default=10,
                        help='Maximum number of images to download per risk (default: 10)')
    parser.add_argument('--csv-file', type=str, default=None,
                        help='Process specific CSV file instead of all files')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='Delay between requests in seconds (default: 2.0)')

    args = parser.parse_args()

    logger.info("Starting image crawler")
    logger.info(f"Используемый поисковый движок: {args.engine}")
    logger.info(f"Максимум изображений на риск: {args.max_images}")

    # Импортируем yandex_crawler если нужно
    if args.engine in ['yandex', 'both']:
        try:
            import yandex_crawler
            logger.info("Модуль yandex_crawler успешно импортирован")
        except ImportError as e:
            logger.error(f"Не удалось импортировать модуль yandex_crawler: {e}")
            if args.engine == 'yandex':
                logger.warning("Переключение на поисковый движок Google")
                args.engine = 'google'

    # Логирование абсолютных путей для отладки
    logger.info(f"Используется директория CSV: {CSV_DIR.absolute()}")
    logger.info(f"Используется директория для загрузки: {DOWNLOAD_DIR.absolute()}")

    # Create download directories if they don't exist
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Check if CSV directory exists
    if not CSV_DIR.exists():
        CSV_DIR.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Директория CSV файлов не существовала и была создана: {CSV_DIR}")
        logger.info(f"Поместите файлы CSV с рисками в директорию {CSV_DIR} перед запуском краулера")

    # Get list of CSV files
    if args.csv_file:
        # Если указан конкретный файл, используем только его
        csv_path = CSV_DIR / args.csv_file
        if csv_path.exists():
            csv_files = [csv_path]
            logger.info(f"Обработка указанного CSV файла: {csv_path.name}")
        else:
            logger.error(f"Указанный CSV файл не найден: {csv_path}")
            csv_files = []
    else:
        # Иначе получаем список всех CSV файлов
        csv_files = get_csv_files()
        logger.info(f"Найдено {len(csv_files)} CSV файлов для обработки")

    # If CSV files are found, display their names
    if csv_files:
        logger.info("Найдены следующие CSV файлы:")
        for file_path in csv_files:
            logger.info(f"  - {file_path.name}")

        # Process each file sequentially
        for file_path in csv_files:
            logger.info(f"Начало обработки файла {file_path.name}")
            process_csv_file(file_path, search_engine=args.engine, max_images=args.max_images, delay=args.delay)
    else:
        logger.warning(f"CSV файлы не найдены в директории {CSV_DIR}. Загрузка изображений невозможна.")

    logger.info("Краулер завершил работу")

if __name__ == "__main__":
    main()