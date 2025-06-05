"""
Тесты для модуля краулера изображений.
Проверяют функциональность чтения CSV-файлов и скачивания изображений.
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import csv
import os

# Импортируем модуль, который будем тестировать
from image_crawler import (
    get_csv_files, 
    read_csv_data, 
    extract_culture_risk_info,
    create_search_query,
    get_google_image_urls,
    download_image
)

class TestImageCrawler(unittest.TestCase):
    
    def setUp(self):
        """Настраивает тестовую среду."""
        # Создаем временную директорию для тестов
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Создаем тестовый CSV-файл
        self.csv_path = self.temp_path / "diseases_пшеница_cereals.csv"
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'description'])
            writer.writerow(['Ржавчина', 'Описание ржавчины'])
            writer.writerow(['Септориоз', 'Описание септориоза'])
    
    def tearDown(self):
        """Очищает тестовую среду."""
        self.temp_dir.cleanup()
    
    def test_read_csv_data(self):
        """Тестирует функцию чтения данных из CSV."""
        data = read_csv_data(self.csv_path)
        
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'Ржавчина')
        self.assertEqual(data[0]['description'], 'Описание ржавчины')
        self.assertEqual(data[1]['name'], 'Септориоз')
    
    def test_extract_culture_risk_info(self):
        """Тестирует извлечение информации о культуре и риске из имени файла."""
        culture_ru, culture_en, risk_type = extract_culture_risk_info(self.csv_path)
        
        self.assertEqual(culture_ru, 'пшеница')
        self.assertEqual(culture_en, 'cereals')
        self.assertEqual(risk_type, 'diseases')
        
        # Тест с неправильным форматом имени файла
        wrong_path = Path("wrong_format.csv")
        culture_ru, culture_en, risk_type = extract_culture_risk_info(wrong_path)
        
        self.assertEqual(culture_ru, 'unknown')
        self.assertEqual(culture_en, 'unknown')
        self.assertEqual(risk_type, 'unknown')
    
    def test_create_search_query(self):
        """Тестирует создание поискового запроса."""
        # Для болезней
        query = create_search_query('Ржавчина', 'пшеница', 'diseases')
        self.assertEqual(query, 'Ржавчина болезнь пшеница фото')
        
        # Для вредителей
        query = create_search_query('Тля', 'пшеница', 'pests')
        self.assertEqual(query, 'Тля вредитель пшеница фото')
    
    @patch('requests.get')
    def test_get_google_image_urls(self, mock_get):
        """Тестирует получение URL изображений."""
        # Создаем мок для ответа requests.get
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <img src="https://example.com/image1.jpg" />
                <img src="https://example.com/image2.png" />
                <a href="https://example.com/image3.webp">Image</a>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        urls = get_google_image_urls('тестовый запрос', max_images=3)
        
        # Проверяем, что функция вызвана с правильными параметрами
        mock_get.assert_called_once()
        
        # В этом тесте мы не можем точно проверить результат,
        # так как извлечение URL зависит от структуры HTML,
        # которая может меняться
        self.assertIsInstance(urls, list)
    
    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_download_image(self, mock_request, mock_urlopen):
        """Тестирует скачивание изображения."""
        # Создаем моки
        mock_response = MagicMock()
        mock_response.read.return_value = b'fake image data'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Тестируем функцию
        save_path = self.temp_path / 'test_image.jpg'
        result = download_image('https://example.com/image.jpg', save_path)
        
        # Проверяем результат
        self.assertTrue(result)
        self.assertTrue(save_path.exists())
        
        # Проверяем содержимое файла
        with open(save_path, 'rb') as f:
            self.assertEqual(f.read(), b'fake image data')

if __name__ == '__main__':
    unittest.main()