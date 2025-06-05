"""
Модуль для генерации дополнительных изображений с помощью Stable Diffusion.
Используется при недостатке реальных изображений для обучения.
"""

import os
import torch
import logging
from pathlib import Path
from typing import List, Dict, Optional
from diffusers import StableDiffusionPipeline
from PIL import Image

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dataset-labeling/stable_diffusion.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("stable_diffusion_augmentation")

# Константы
GENERATED_IMAGES_DIR = Path("dataset-labeling/generated_images")
GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def load_stable_diffusion_model(model_id: str = "runwayml/stable-diffusion-v1-5") -> StableDiffusionPipeline:
    """
    Загружает модель Stable Diffusion.
    
    Args:
        model_id: Идентификатор модели.
        
    Returns:
        Загруженный пайплайн Stable Diffusion.
    """
    try:
        # Проверяем доступность CUDA
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Загружаем модель
        pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
        pipe = pipe.to(device)
        
        # Для экономии памяти на GPU
        if device == "cuda":
            pipe.enable_attention_slicing()
        
        logger.info(f"Модель Stable Diffusion загружена на устройство: {device}")
        return pipe
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели Stable Diffusion: {e}")
        raise

def generate_images(
    pipe: StableDiffusionPipeline,
    prompt: str,
    num_images: int = 5,
    guidance_scale: float = 7.5,
    num_inference_steps: int = 50,
    save_dir: Optional[Path] = None
) -> List[Image.Image]:
    """
    Генерирует изображения с помощью Stable Diffusion.
    
    Args:
        pipe: Пайплайн Stable Diffusion.
        prompt: Текстовый запрос для генерации.
        num_images: Количество изображений для генерации.
        guidance_scale: Степень соответствия запросу.
        num_inference_steps: Количество шагов вывода.
        save_dir: Директория для сохранения изображений.
        
    Returns:
        Список сгенерированных изображений.
    """
    logger.info(f"Генерация {num_images} изображений для запроса: {prompt}")
    
    try:
        # Генерируем изображения
        images = []
        
        # Генерируем по одному изображению, чтобы избежать проблем с памятью
        for i in range(num_images):
            result = pipe(
                prompt,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps
            )
            
            image = result.images[0]
            images.append(image)
            
            # Сохраняем изображение, если указана директория
            if save_dir:
                # Создаем безопасное имя файла из запроса
                safe_prompt = "".join([c if c.isalnum() else "_" for c in prompt])
                safe_prompt = safe_prompt[:50]  # Ограничиваем длину
                
                image_path = save_dir / f"{safe_prompt}_{i}.png"
                image.save(image_path)
                logger.info(f"Изображение сохранено: {image_path}")
        
        return images
    
    except Exception as e:
        logger.error(f"Ошибка при генерации изображений: {e}")
        raise

def create_prompt_for_risk(risk_name: str, culture: str, risk_type: str, language: str = "russian") -> str:
    """
    Создает запрос для Stable Diffusion на основе информации о риске.
    
    Args:
        risk_name: Название риска (болезни или вредителя).
        culture: Название культуры.
        risk_type: Тип риска (diseases или pests).
        language: Язык запроса ("russian" или "english").
        
    Returns:
        Текстовый запрос для Stable Diffusion.
    """
    if language == "russian":
        if risk_type == "diseases":
            return f"Фотография болезни '{risk_name}' на растении {culture}, крупный план, высокое качество, фото болезни растения"
        else:  # pests
            return f"Фотография вредителя '{risk_name}' на растении {culture}, крупный план, высокое качество, фото вредителя растения"
    else:  # english
        if risk_type == "diseases":
            return f"Photograph of '{risk_name}' disease on {culture} plant, close-up, high quality, photo of plant disease"
        else:  # pests
            return f"Photograph of '{risk_name}' pest on {culture} plant, close-up, high quality, photo of plant pest"

def generate_images_for_risks(
    risk_data: List[Dict[str, str]],
    min_images_per_risk: int = 10,
    max_generate: int = 5
) -> None:
    """
    Генерирует изображения для рисков, у которых недостаточно изображений.
    
    Args:
        risk_data: Список словарей с информацией о рисках.
        min_images_per_risk: Минимальное количество изображений для каждого риска.
        max_generate: Максимальное количество изображений для генерации.
    """
    logger.info("Начало генерации изображений для рисков")
    
    # Загружаем модель Stable Diffusion
    pipe = load_stable_diffusion_model()
    
    # Проходим по данным о рисках
    for risk_info in risk_data:
        risk_name = risk_info['name']
        culture = risk_info['culture']
        risk_type = risk_info['risk_type']
        
        # Путь к директории с изображениями для данного риска
        images_dir = Path("crawler/downloads/images") / risk_type / culture / risk_name.replace(' ', '_').lower()
        
        # Если директория не существует, создаем ее
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Получаем список существующих изображений
        existing_images = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.jpeg')) + \
                         list(images_dir.glob('*.png')) + list(images_dir.glob('*.webp'))
        
        # Если изображений достаточно, пропускаем
        if len(existing_images) >= min_images_per_risk:
            logger.info(f"Для {risk_name} ({culture}, {risk_type}) уже есть {len(existing_images)} изображений, пропускаем")
            continue
        
        # Определяем количество изображений для генерации
        num_to_generate = min(min_images_per_risk - len(existing_images), max_generate)
        
        logger.info(f"Для {risk_name} ({culture}, {risk_type}) нужно сгенерировать {num_to_generate} изображений")
        
        # Создаем запросы на русском и английском
        prompt_ru = create_prompt_for_risk(risk_name, culture, risk_type, "russian")
        prompt_en = create_prompt_for_risk(risk_name, culture, risk_type, "english")
        
        # Генерируем изображения с русским запросом
        num_ru = num_to_generate // 2 + num_to_generate % 2
        if num_ru > 0:
            try:
                generate_images(pipe, prompt_ru, num_ru, save_dir=images_dir)
            except Exception as e:
                logger.error(f"Ошибка при генерации изображений (RU): {e}")
        
        # Генерируем изображения с английским запросом
        num_en = num_to_generate // 2
        if num_en > 0:
            try:
                generate_images(pipe, prompt_en, num_en, save_dir=images_dir)
            except Exception as e:
                logger.error(f"Ошибка при генерации изображений (EN): {e}")
    
    logger.info("Генерация изображений завершена")

def main():
    """
    Основная функция для генерации изображений.
    """
    # Пример данных о рисках
    risk_data = [
        {
            'name': 'Ржавчина',
            'culture': 'пшеница',
            'risk_type': 'diseases'
        },
        {
            'name': 'Тля',
            'culture': 'пшеница',
            'risk_type': 'pests'
        }
        # Добавьте другие риски по необходимости
    ]
    
    # Генерируем изображения
    generate_images_for_risks(risk_data)

if __name__ == "__main__":
    main()