#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для пакетного преобразования изображений WEBP в формат JPG.
Проходит по всем подпапкам в указанной директории и конвертирует все WEBP файлы в JPG.
"""

import os
import argparse
from PIL import Image
import logging
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webp_converter.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("WebpConverter")


def is_valid_risk_filename(filename):
    """
    Проверяет соответствует ли имя файла шаблону risk_type_culture_guid_number.ext
    """
    pattern = r'^(diseases|pests|weeds)_[a-z]+_[a-f0-9\-]+_\d+\.\w+$'
    return bool(re.match(pattern, filename.lower()))


def fix_filename(filename, filepath):
    """
    Исправляет имя файла в соответствии с требуемым шаблоном, если оно не соответствует
    """
    if is_valid_risk_filename(filename):
        return filename

    # Попытка извлечь компоненты из пути к файлу
    path_parts = os.path.normpath(filepath).split(os.sep)

    # Ищем компоненты в пути к файлу
    risk_type = None
    culture = None
    guid = None

    for part in path_parts:
        # Проверяем на тип риска
        if part.lower() in ['diseases', 'pests', 'weeds']:
            risk_type = part.lower()

        # Проверяем на GUID
        if re.match(r'^[a-f0-9\-]+$', part) and len(part) > 30:
            guid = part

    # Если не можем извлечь все компоненты, сохраняем оригинальное имя
    if not (risk_type and guid):
        return filename

    # Получаем culture из предпоследнего уровня директории
    culture_index = None
    for i, part in enumerate(path_parts):
        if part == guid and i > 0:
            culture = path_parts[i-1].lower()
            break

    # Если все еще не можем определить культуру
    if not culture:
        culture = "unknown"

    # Извлекаем номер из оригинального имени или присваиваем новый
    number_match = re.search(r'_(\d+)\.', filename)
    if number_match:
        number = number_match.group(1)
    else:
        number = "00"

    # Получаем расширение
    _, ext = os.path.splitext(filename)

    # Создаем новое имя файла
    new_filename = f"{risk_type}_{culture}_{guid}_{number}{ext}"
    return new_filename


def convert_webp_to_jpg(file_path, delete_original=True, quality=95):
    """
    Конвертирует WEBP файл в JPG формат

    Args:
        file_path (str): Путь к WEBP файлу
        delete_original (bool): Удалить оригинальный WEBP файл после конвертации
        quality (int): Качество JPG (от 1 до 100)

    Returns:
        str: Путь к новому JPG файлу или None в случае ошибки
    """
    if not file_path.lower().endswith('.webp'):
        return None

    try:
        # Открываем WEBP изображение
        img = Image.open(file_path)

        # Путь для сохранения JPG (заменяем расширение)
        jpg_path = os.path.splitext(file_path)[0] + '.jpg'

        # Конвертируем в RGB (JPG не поддерживает прозрачность)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGB')

        # Сохраняем как JPG
        img.save(jpg_path, 'JPEG', quality=quality)

        # Закрываем изображение
        img.close()

        # Удаляем оригинальный WEBP файл при необходимости
        if delete_original:
            os.remove(file_path)

        logger.info(f"Преобразовано: {file_path} -> {jpg_path}")
        return jpg_path

    except Exception as e:
        logger.error(f"Ошибка при конвертации {file_path}: {e}")
        return None


def process_directory(directory, fix_names=True):
    """
    Обрабатывает директорию и все поддиректории, конвертируя WEBP в JPG

    Args:
        directory (str): Путь к директории для обработки
        fix_names (bool): Исправлять имена файлов по шаблону
    """
    converted_count = 0
    renamed_count = 0

    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)

            # Конвертация WEBP в JPG
            if filename.lower().endswith('.webp'):
                new_path = convert_webp_to_jpg(file_path)
                if new_path:
                    converted_count += 1
                    file_path = new_path
                    filename = os.path.basename(new_path)

            # Исправление имени файла по шаблону
            if fix_names and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                if not is_valid_risk_filename(filename):
                    new_filename = fix_filename(filename, file_path)
                    if new_filename != filename:
                        new_path = os.path.join(root, new_filename)
                        try:
                            os.rename(file_path, new_path)
                            logger.info(f"Переименовано: {filename} -> {new_filename}")
                            renamed_count += 1
                        except Exception as e:
                            logger.error(f"Ошибка при переименовании {file_path}: {e}")

    logger.info(f"Всего конвертировано файлов: {converted_count}")
    logger.info(f"Всего переименовано файлов: {renamed_count}")


def main():
    parser = argparse.ArgumentParser(description="Конвертирует WEBP изображения в формат JPG")
    parser.add_argument(
        "--directory", "-d",
        type=str, 
        default="download",
        help="Директория для обработки"
    )
    parser.add_argument(
        "--fix-names", "-f",
        action="store_true",
        help="Исправлять имена файлов по шаблону risk_type_culture_guid_number.ext"
    )

    args = parser.parse_args()

    logger.info(f"Начало обработки директории: {args.directory}")
    process_directory(args.directory, args.fix_names)
    logger.info("Обработка завершена")


if __name__ == "__main__":
    main()
