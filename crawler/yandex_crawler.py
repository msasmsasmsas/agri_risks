"""Module for searching images in Yandex Images."""

import logging
import random
import re
import time
import urllib.parse
from typing import List, Optional

import requests

# Получаем логгер из основного модуля
logger = logging.getLogger("image_crawler")

# Список User-Agent для использования при запросах
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]


def get_yandex_image_urls(query: str, max_images: int = 10) -> List[str]:
    """
    Gets image URLs from Yandex Images for a given query.

    Args:
        query: Search query
        max_images: Maximum number of images to download

    Returns:
        List of image URLs
    """
    query_encoded = urllib.parse.quote(query)
    search_url = f"https://yandex.ru/images/search?text={query_encoded}"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
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
        logger.info(f"Поиск изображений в Яндекс по запросу: {query}")
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Извлечение URL изображений из HTML
        image_urls = []

        # Регулярное выражение для поиска URL изображений в Яндексе
        # Яндекс хранит URL в JSON-структуре внутри HTML
        pattern = r'"orig_url":"(https://[^"]+\.(?:jpg|jpeg|png|webp))"'
        try:
            found_urls = re.findall(pattern, response.text)

            # Фильтрация URL
            for url in found_urls:
                # Удаляем экранирование обратного слеша
                url = url.replace("\\", "")
                if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    image_urls.append(url)
                    if len(image_urls) >= max_images:
                        break

            if not image_urls:
                logger.warning(f"Не найдено изображений в Яндексе для запроса: {query}")
            else:
                logger.info(f"Найдено {len(image_urls)} изображений в Яндексе для запроса: {query}")

        except Exception as e:
            logger.error(f"Ошибка при поиске URL изображений в ответе Яндекса: {e}")

        return image_urls
    except Exception as e:
        logger.error(f"Ошибка при получении изображений из Яндекса: {e}")
        return []


def get_images_with_fallback(query: str, max_images: int = 10) -> List[str]:
    """
    Gets image URLs using Yandex first, then falls back to Google if needed.

    Args:
        query: Search query
        max_images: Maximum number of images to download

    Returns:
        List of image URLs
    """
    # Попытка получить изображения из Яндекса
    image_urls = get_yandex_image_urls(query, max_images)

    # Если изображения не найдены в Яндексе, используем Google как запасной вариант
    if not image_urls:
        logger.info(f"Переключение на Google для запроса: {query}")
        from ImageCrawler import get_google_image_urls
        image_urls = get_google_image_urls(query, max_images)

    return image_urls
