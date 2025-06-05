"""
Google Gemini API client.
Implements an interface for recognizing risks in crop images.
"""

import os
import base64
import logging
import requests
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from PIL import Image
import io
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gemini-integration/gemini.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gemini_client")

class GeminiClient:
    """
    Клиент для работы с Google Gemini API.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro-vision"):
        """
        Инициализирует клиент Gemini API.
        
        Args:
            api_key: API ключ для доступа к Gemini API. Если не указан, берется из переменной окружения GEMINI_API_KEY из .env файла.
            model: Название модели Gemini для использования.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API ключ не указан и не найден в переменной окружения GEMINI_API_KEY в .env файле")
            
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        logger.info(f"Инициализирован клиент Gemini API с моделью {self.model}")
    
    def encode_image(self, image_path: Union[str, Path]) -> str:
        """
        Кодирует изображение в base64.
        
        Args:
            image_path: Путь к изображению.
            
        Returns:
            Изображение, закодированное в base64.
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def encode_image_from_pil(self, image: Image.Image, format: str = "JPEG") -> str:
        """
        Кодирует PIL изображение в base64.
        
        Args:
            image: PIL изображение.
            format: Формат для сохранения изображения.
            
        Returns:
            Изображение, закодированное в base64.
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def analyze_image(self, 
                      image_path: Union[str, Path, Image.Image], 
                      prompt: Optional[str] = None, 
                      temperature: float = 0.4,
                      max_output_tokens: int = 1024) -> Dict[str, Any]:
        """
        Анализирует изображение с помощью Gemini API.
        
        Args:
            image_path: Путь к изображению или PIL изображение.
            prompt: Запрос для модели. Если не указан, используется стандартный запрос.
            temperature: Температура для генерации (от 0 до 1).
            max_output_tokens: Максимальное количество токенов в ответе.
            
        Returns:
            Словарь с результатами анализа.
        """
        # Кодируем изображение
        if isinstance(image_path, (str, Path)):
            encoded_image = self.encode_image(image_path)
        else:  # PIL Image
            encoded_image = self.encode_image_from_pil(image_path)
        
        # Формируем стандартный запрос, если не указан
        if prompt is None:
            prompt = """
            Проанализируй это изображение сельскохозяйственной культуры.
            Определи, есть ли на нем признаки болезней или вредителей.
            
            Если есть признаки болезни:
            1. Укажи название болезни
            2. Опиши симптомы, которые видны на изображении
            3. Оцени степень поражения (легкая, средняя, тяжелая)
            4. Предложи возможные меры борьбы
            
            Если есть признаки вредителей:
            1. Укажи название вредителя
            2. Опиши признаки его присутствия на изображении
            3. Оцени уровень вреда (низкий, средний, высокий)
            4. Предложи возможные меры борьбы
            
            Если нет признаков болезней или вредителей, укажи это.
            
            Ответ структурируй в формате JSON со следующими полями:
            {
                "risk_detected": true/false,
                "risk_type": "disease" или "pest" или "none",
                "name": "название болезни или вредителя",
                "symptoms": "описание симптомов или признаков",
                "severity": "легкая/средняя/тяжелая или низкий/средний/высокий",
                "recommendations": ["рекомендация 1", "рекомендация 2", ...]
            }
            """
        
        # Формируем запрос к API
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": encoded_image
                        }
                    }
                ]
            }],
            "generation_config": {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens
            }
        }
        
        # Отправляем запрос
        url = f"{self.base_url}?key={self.api_key}"
        try:
            logger.info("Отправка запроса к Gemini API")
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            # Обрабатываем ответ
            response_data = response.json()
            
            # Извлекаем текст ответа
            text_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            # Пытаемся извлечь JSON из ответа
            try:
                # Ищем JSON в тексте
                json_start = text_response.find('{')
                json_end = text_response.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = text_response[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    # Если JSON не найден, возвращаем текст как есть
                    result = {"raw_response": text_response}
            except json.JSONDecodeError:
                result = {"raw_response": text_response}
            
            logger.info("Получен ответ от Gemini API")
            return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к Gemini API: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Непредвиденная ошибка: {e}")
            return {"error": str(e)}
    
    def analyze_images_batch(self, 
                           image_paths: List[Union[str, Path, Image.Image]], 
                           prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Анализирует пакет изображений с помощью Gemini API.
        
        Args:
            image_paths: Список путей к изображениям или PIL изображений.
            prompt: Запрос для модели. Если не указан, используется стандартный запрос.
            
        Returns:
            Список словарей с результатами анализа.
        """
        results = []
        for image_path in image_paths:
            result = self.analyze_image(image_path, prompt)
            results.append(result)
        return results

def main():
    """
    Main function for testing the Gemini API client.
    """
    # Load API key from .env file
    api_key = os.environ.get("GEMINI_API_KEY")

    # Initialize client
    client = GeminiClient(api_key)

    # Analyze test image
    test_image_path = "path/to/test_image.jpg"  # Replace with path to test image

    if os.path.exists(test_image_path):
        result = client.analyze_image(test_image_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Test image not found: {test_image_path}")

if __name__ == "__main__":
    main()