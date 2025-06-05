#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для конвертации WEBP изображений в JPG
"""

import os
import re
import sys
import argparse
from pathlib import Path
from PIL import Image
import logging
import uuid

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("converter.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("webp_converter")


def convert_webp_to_jpg(file_path, delete_original=True, quality=95):
    """
    Конвертирует WEBP файл в JPG
    """
    if not file_path.lower().endswith('.webp'):
        return None

    try:
        img = Image.open(file_path)
        jpg_path = file_path.replace('.webp', '.jpg').replace('.WEBP', '.jpg')

        # JPG не поддерживает прозрачность, конвертируем в RGB
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGB')

        img.save(jpg_path, 'JPEG', quality=quality)
        img.close()

        if delete_original:
            os.remove(file_path)

        return jpg_path
    except Exception as e:
        logger.error(f"Ошибка при конвертации {file_path}: {e}")
        return None


def rename_file_according_to_pattern(file_path):
    """
    Переименовывает файл в соответствии с шаблоном: risk_type_culture_guid_number.jpg
    """
    try:
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)

        # Извлечь тип риска из структуры директорий
        path_parts = os.path.normpath(directory).split(os.sep)
        risk_types = ['diseases', 'pests', 'weeds']
        risk_type = next((part for part in path_parts if part.lower() in risk_types), 'unknown')

        # Извлечь культуру из структуры директорий (обычно идет после типа риска)
        culture = 'unknown'
        disease_name = 'unknown'
        for i, part in enumerate(path_parts):
            if part.lower() in risk_types and i+1 < len(path_parts):
                culture = path_parts[i+1].lower()
                # Попытаться получить название болезни из последнего элемента пути
                if i+2 < len(path_parts):
                    disease_name = path_parts[i+2].lower()
                break

        # Поиск GUID в имени файла или пути
        guid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        guid_match = re.search(guid_pattern, file_path)

        if guid_match:
            guid = guid_match.group(0)
        else:
            # Проверить, содержится ли GUID в пути директории
            dir_guid_match = re.search(guid_pattern, directory)
            if dir_guid_match:
                guid = dir_guid_match.group(0)
            else:
                # Если GUID не найден, генерируем на основе типа риска, культуры и названия болезни
                # для обеспечения единого GUID для всех фото одной болезни
                guid_seed = f"{risk_type}_{culture}_{disease_name}".lower()
                guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, guid_seed))

        # Определить номер файла
        number_match = re.search(r'_(\d+)\.[a-z]+$', filename)
        if number_match:
            number = number_match.group(1)
        else:
            # Если номер не найден, используем случайное число от 1 до 99
            number = f"{random.randint(1, 99):02d}"

        # Создать новое имя файла по шаблону
        extension = os.path.splitext(filename)[1]
        if not extension:
            extension = '.jpg'

        new_filename = f"{risk_type}_{culture}_{guid}_{number}{extension}"
        new_path = os.path.join(directory, new_filename)

        # Переименовать файл
        os.rename(file_path, new_path)
        logger.info(f"Файл переименован: {filename} -> {new_filename}")

        return new_path
    except Exception as e:
        logger.error(f"Ошибка при переименовании файла {file_path}: {e}")
        return file_path


def process_directory(directory, rename=True, recursive=True):
    """
    Обрабатывает директорию и конвертирует все найденные WEBP файлы в JPG
    """
    if not os.path.exists(directory):
        logger.error(f"Директория не существует: {directory}")
        return

    files_to_process = []

    # Собираем все файлы для обработки
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.webp'):
                    files_to_process.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            if file.lower().endswith('.webp'):
                files_to_process.append(os.path.join(directory, file))

    logger.info(f"Найдено {len(files_to_process)} WEBP файлов для конвертации")

    # Обрабатываем каждый файл
    converted_count = 0
    renamed_count = 0

    for file_path in files_to_process:
        # Конвертация WEBP в JPG
        jpg_path = convert_webp_to_jpg(file_path)
        if jpg_path:
            converted_count += 1

            # Переименование в соответствии с шаблоном
            if rename and jpg_path:
                new_path = rename_file_according_to_pattern(jpg_path)
                if new_path != jpg_path:
                    renamed_count += 1

    # Также переименовываем существующие JPG/JPEG файлы если требуется
    if rename:
        jpg_files = []
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg')) and not re.search(r'_(\d+)\.[a-z]+$', file):
                        jpg_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if file.lower().endswith(('.jpg', '.jpeg')) and not re.search(r'_(\d+)\.[a-z]+$', file):
                    jpg_files.append(os.path.join(directory, file))

        logger.info(f"Найдено {len(jpg_files)} JPG файлов для переименования")

        for jpg_path in jpg_files:
            new_path = rename_file_according_to_pattern(jpg_path)
            if new_path != jpg_path:
                renamed_count += 1

    logger.info(f"Конвертировано {converted_count} из {len(files_to_process)} WEBP файлов")
    logger.info(f"Переименовано {renamed_count} файлов")


def main():
    parser = argparse.ArgumentParser(description="Конвертер WEBP в JPG")
    parser.add_argument(
        "--directory", "-d",
        default="download/images",
        help="Директория для обработки (по умолчанию: download/images)"
    )
    parser.add_argument(
        "--rename", "-r",
        action="store_true",
        help="Переименовать файлы в соответствии с шаблоном risk_type_culture_guid_number.jpg"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Не обрабатывать поддиректории"
    )

    args = parser.parse_args()

    directory = args.directory
    if not os.path.isabs(directory):
        # Если путь не абсолютный, считаем его относительным текущего скрипта
        script_dir = os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(script_dir, directory)

    logger.info(f"Начинаем обработку директории: {directory}")
    process_directory(directory, rename=args.rename, recursive=not args.no_recursive)
    logger.info("Обработка завершена")


if __name__ == "__main__":
    main()
