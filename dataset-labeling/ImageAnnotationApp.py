"""
Приложение для ручной разметки изображений.
Использует Gradio для создания веб-интерфейса.
"""

import os
import json
import shutil
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import cv2
import gradio as gr

from dataset_utils import IMAGES_SOURCE_DIR, DATASET_DIR, load_classes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dataset-labeling/labeling_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("labeling_app")

# Константы
LABELS_DIR = DATASET_DIR / "manual_labels"
LABELS_DIR.mkdir(parents=True, exist_ok=True)

def get_image_list() -> List[str]:
    """
    Получает список всех изображений из IMAGES_SOURCE_DIR.
    
    Returns:
        Список путей к изображениям.
    """
    image_paths = []
    
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
                    
                # Получаем изображения
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
                    for img_path in risk_dir.glob(ext):
                        image_paths.append(str(img_path))
    
    logger.info(f"Найдено {len(image_paths)} изображений для разметки")
    return image_paths

def save_annotation(image_path: str, boxes: List[List[float]], class_indices: List[int]) -> None:
    """
    Сохраняет аннотацию в формате YOLO.
    
    Args:
        image_path: Путь к изображению.
        boxes: Список боксов в формате [x1, y1, x2, y2].
        class_indices: Список индексов классов для каждого бокса.
    """
    img_path = Path(image_path)
    label_path = LABELS_DIR / f"{img_path.stem}.txt"
    
    # Загружаем изображение для получения размеров
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    
    with open(label_path, 'w', encoding='utf-8') as f:
        for box, class_idx in zip(boxes, class_indices):
            # Конвертируем координаты из абсолютных в относительные
            x1, y1, x2, y2 = box
            x_center = (x1 + x2) / 2 / w
            y_center = (y1 + y2) / 2 / h
            width = (x2 - x1) / w
            height = (y2 - y1) / h
            
            # Записываем в формате YOLO: class_idx x_center y_center width height
            f.write(f"{class_idx} {x_center} {y_center} {width} {height}\n")
    
    logger.info(f"Сохранена аннотация для {image_path}")

def create_gradio_interface():
    """
    Создает интерфейс Gradio для разметки изображений.
    """
    classes = load_classes()
    if not classes:
        logger.error("Не удалось загрузить классы")
        return
    
    # Получаем список изображений
    image_paths = get_image_list()
    if not image_paths:
        logger.error("Не найдено изображений для разметки")
        return
    
    # Создаем интерфейс Gradio
    with gr.Blocks(title="Разметка изображений для YOLOv11") as interface:
        gr.Markdown("# Инструмент для разметки изображений сельхоз культур")
        
        with gr.Row():
            with gr.Column(scale=3):
                image_input = gr.Image(label="Изображение", type="filepath")
                annotated_image = gr.Image(label="Размеченное изображение")
            
            with gr.Column(scale=1):
                class_dropdown = gr.Dropdown(choices=classes, label="Класс")
                add_button = gr.Button("Добавить бокс")
                clear_button = gr.Button("Очистить разметку")
                save_button = gr.Button("Сохранить")
                next_button = gr.Button("Следующее изображение")
        
        # Состояние для хранения текущих боксов и классов
        boxes_state = gr.State([])
        class_indices_state = gr.State([])
        current_image_idx = gr.State(0)
        
        # Функция для обновления изображения с боксами
        def update_image(image, boxes, class_indices):
            if image is None:
                return None
            
            img = cv2.imread(image)
            for box, class_idx in zip(boxes, class_indices):
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, classes[class_idx], (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Функция для добавления бокса
        def add_box(image, boxes, class_indices, class_idx):
            if image is None:
                return boxes, class_indices, None
            
            img = cv2.imread(image)
            h, w = img.shape[:2]
            
            # Добавляем бокс в центре изображения (50% размера)
            x1 = int(w * 0.25)
            y1 = int(h * 0.25)
            x2 = int(w * 0.75)
            y2 = int(h * 0.75)
            
            new_boxes = boxes + [[x1, y1, x2, y2]]
            new_class_indices = class_indices + [classes.index(class_idx)]
            
            return new_boxes, new_class_indices, update_image(image, new_boxes, new_class_indices)
        
        # Функция для очистки разметки
        def clear_annotation(image):
            if image is None:
                return [], [], None
            
            return [], [], cv2.cvtColor(cv2.imread(image), cv2.COLOR_BGR2RGB)
        
        # Функция для сохранения аннотации
        def save_annotation_ui(image, boxes, class_indices):
            if image is None or not boxes:
                return "Нет данных для сохранения"
            
            save_annotation(image, boxes, class_indices)
            return f"Аннотация сохранена: {len(boxes)} боксов"
        
        # Функция для перехода к следующему изображению
        def next_image(idx):
            next_idx = (idx + 1) % len(image_paths)
            return image_paths[next_idx], next_idx, [], [], None
        
        # Инициализация первого изображения
        def init_interface(idx):
            return image_paths[idx], idx
        
        # Привязываем функции к событиям
        add_button.click(
            add_box,
            [image_input, boxes_state, class_indices_state, class_dropdown],
            [boxes_state, class_indices_state, annotated_image]
        )
        
        clear_button.click(
            clear_annotation,
            [image_input],
            [boxes_state, class_indices_state, annotated_image]
        )
        
        save_button.click(
            save_annotation_ui,
            [image_input, boxes_state, class_indices_state],
            [gr.Textbox(label="Статус")]
        )
        
        next_button.click(
            next_image,
            [current_image_idx],
            [image_input, current_image_idx, boxes_state, class_indices_state, annotated_image]
        )
        
        # Инициализация интерфейса
        interface.load(
            init_interface,
            [current_image_idx],
            [image_input, current_image_idx]
        )
    
    # Запускаем интерфейс
    interface.launch(share=True)

if __name__ == "__main__":
    create_gradio_interface()