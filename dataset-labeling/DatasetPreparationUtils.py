"""
Утилиты для работы с датасетом.
Включает функции для конвертации форматов разметки, аугментации данных и т.д.
"""

import os
import json
import shutil
import random
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import logging
import cv2

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dataset-labeling/dataset.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dataset_utils")

# Константы
IMAGES_SOURCE_DIR = Path("crawler/downloads/images")
DATASET_DIR = Path("dataset-labeling/dataset")
CLASSES_FILE = DATASET_DIR / "classes.txt"

def setup_dataset_directories() -> None:
    """
    Создает структуру директорий для датасета.
    """
    for split in ['train', 'val', 'test']:
        for subdir in ['images', 'labels']:
            path = DATASET_DIR / split / subdir
            path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Созданы директории датасета в {DATASET_DIR}")

def collect_classes() -> List[str]:
    """
    Собирает список классов на основе структуры директорий с изображениями.
    
    Returns:
        Список классов (имена директорий с изображениями).
    """
    classes = []
    
    # Проходим по директориям с болезнями и вредителями
    for risk_type in ['diseases', 'pests']:
        risk_dir = IMAGES_SOURCE_DIR / risk_type
        if not risk_dir.exists():
            continue
            
        # Проходим по культурам
        for culture_dir in risk_dir.iterdir():
            if not culture_dir.is_dir():
                continue
                
            # Проходим по рискам (болезням/вредителям)
            for risk_dir in culture_dir.iterdir():
                if not risk_dir.is_dir():
                    continue
                    
                # Формируем имя класса в формате "risk_type_culture_risk_name"
                class_name = f"{risk_type}_{culture_dir.name}_{risk_dir.name}"
                classes.append(class_name)
    
    logger.info(f"Собрано {len(classes)} классов")
    return classes

def save_classes(classes: List[str]) -> None:
    """
    Сохраняет список классов в файл.
    
    Args:
        classes: Список классов.
    """
    with open(CLASSES_FILE, 'w', encoding='utf-8') as f:
        for cls in classes:
            f.write(f"{cls}\n")
    
    logger.info(f"Список классов сохранен в {CLASSES_FILE}")

def load_classes() -> List[str]:
    """
    Загружает список классов из файла.
    
    Returns:
        Список классов.
    """
    if not CLASSES_FILE.exists():
        logger.warning(f"Файл классов {CLASSES_FILE} не найден")
        return []
        
    with open(CLASSES_FILE, 'r', encoding='utf-8') as f:
        classes = [line.strip() for line in f.readlines()]
    
    logger.info(f"Загружено {len(classes)} классов из {CLASSES_FILE}")
    return classes

def split_dataset(train_ratio: float = 0.7, val_ratio: float = 0.15, test_ratio: float = 0.15) -> Dict[str, List[Path]]:
    """
    Разделяет датасет на обучающую, валидационную и тестовую выборки.
    
    Args:
        train_ratio: Доля изображений для обучающей выборки.
        val_ratio: Доля изображений для валидационной выборки.
        test_ratio: Доля изображений для тестовой выборки.
        
    Returns:
        Словарь с путями к изображениям для каждой выборки.
    """
    # Проверка соотношений
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-10:
        logger.error("Сумма соотношений должна быть равна 1.0")
        raise ValueError("Сумма соотношений должна быть равна 1.0")
    
    # Словарь для хранения путей изображений
    dataset_splits = {
        'train': [],
        'val': [],
        'test': []
    }
    
    classes = load_classes()
    if not classes:
        logger.error("Не удалось загрузить классы")
        return dataset_splits
    
    # Для каждого класса разделяем изображения
    for class_name in classes:
        parts = class_name.split('_')
        if len(parts) < 3:
            logger.warning(f"Неправильный формат класса: {class_name}, пропускаем")
            continue
            
        risk_type = parts[0]
        culture = parts[1]
        risk_name = '_'.join(parts[2:])
        
        # Путь к директории с изображениями
        images_dir = IMAGES_SOURCE_DIR / risk_type / culture / risk_name
        if not images_dir.exists():
            logger.warning(f"Директория {images_dir} не найдена, пропускаем")
            continue
            
        # Получаем список изображений
        images = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.jpeg')) + \
                 list(images_dir.glob('*.png')) + list(images_dir.glob('*.webp'))
        
        if not images:
            logger.warning(f"Нет изображений в {images_dir}, пропускаем")
            continue
            
        # Перемешиваем изображения
        random.shuffle(images)
        
        # Вычисляем количество изображений для каждой выборки
        n_train = int(len(images) * train_ratio)
        n_val = int(len(images) * val_ratio)
        
        # Разделяем изображения
        train_images = images[:n_train]
        val_images = images[n_train:n_train + n_val]
        test_images = images[n_train + n_val:]
        
        # Добавляем пути в словарь
        dataset_splits['train'].extend(train_images)
        dataset_splits['val'].extend(val_images)
        dataset_splits['test'].extend(test_images)
    
    # Выводим информацию о разделении
    for split, images in dataset_splits.items():
        logger.info(f"Выборка {split}: {len(images)} изображений")
    
    return dataset_splits

def copy_images_to_dataset(dataset_splits: Dict[str, List[Path]]) -> None:
    """
    Копирует изображения в соответствующие директории датасета.
    
    Args:
        dataset_splits: Словарь с путями к изображениям для каждой выборки.
    """
    classes = load_classes()
    if not classes:
        logger.error("Не удалось загрузить классы")
        return
    
    # Создаем словарь для быстрого поиска индекса класса
    class_to_idx = {cls: idx for idx, cls in enumerate(classes)}
    
    # Для каждой выборки копируем изображения и создаем метки
    for split, images in dataset_splits.items():
        dest_images_dir = DATASET_DIR / split / 'images'
        dest_labels_dir = DATASET_DIR / split / 'labels'
        
        for img_path in images:
            # Определяем класс по пути изображения
            parts = img_path.parts
            risk_type = parts[-3]
            culture = parts[-2]
            risk_name = parts[-1]
            
            class_name = f"{risk_type}_{culture}_{risk_name}"
            
            if class_name not in class_to_idx:
                logger.warning(f"Класс {class_name} не найден в списке классов, пропускаем")
                continue
                
            class_idx = class_to_idx[class_name]
            
            # Копируем изображение
            dest_img_path = dest_images_dir / img_path.name
            shutil.copy2(img_path, dest_img_path)
            
            # Создаем YOLO-формат метки
            # Предполагаем, что каждое изображение содержит один объект,
            # занимающий центральную часть изображения
            try:
                img = cv2.imread(str(img_path))
                if img is None:
                    logger.warning(f"Не удалось прочитать изображение {img_path}, пропускаем")
                    continue
                    
                h, w = img.shape[:2]
                
                # Центр и размеры bounding box (предположим, что объект занимает 80% изображения)
                x_center = 0.5
                y_center = 0.5
                width = 0.8
                height = 0.8
                
                # Создаем метку в формате YOLO
                label_path = dest_labels_dir / f"{img_path.stem}.txt"
                with open(label_path, 'w') as f:
                    f.write(f"{class_idx} {x_center} {y_center} {width} {height}\n")
            
            except Exception as e:
                logger.error(f"Ошибка при обработке {img_path}: {e}")
    
    logger.info("Изображения и метки скопированы в директории датасета")

def create_yolo_config() -> None:
    """
    Создает конфигурационный файл для YOLOv11.
    """
    classes = load_classes()
    if not classes:
        logger.error("Не удалось загрузить классы")
        return
    
    # Создаем конфигурационный файл data.yaml
    config = {
        'path': str(DATASET_DIR),
        'train': str(DATASET_DIR / 'train' / 'images'),
        'val': str(DATASET_DIR / 'val' / 'images'),
        'test': str(DATASET_DIR / 'test' / 'images'),
        'nc': len(classes),
        'names': classes
    }
    
    # Сохраняем конфигурацию
    config_path = DATASET_DIR / 'data.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        for key, value in config.items():
            if key == 'names':
                f.write(f"{key}: {value}\n")
            else:
                f.write(f"{key}: {value}\n")
    
    logger.info(f"Конфигурационный файл создан: {config_path}")

def main():
    """
    Основная функция для создания датасета.
    """
    logger.info("Начало создания датасета")
    
    # Создаем директории для датасета
    setup_dataset_directories()
    
    # Собираем и сохраняем классы
    classes = collect_classes()
    save_classes(classes)
    
    # Разделяем датасет
    dataset_splits = split_dataset()
    
    # Копируем изображения и создаем метки
    copy_images_to_dataset(dataset_splits)
    
    # Создаем конфигурационный файл
    create_yolo_config()
    
    logger.info("Датасет создан")

if __name__ == "__main__":
    main()