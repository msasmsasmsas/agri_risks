# Проект по распознаванию рисков сельхозкультур

## Команды для запуска краулера

```bash
# Установка зависимостей для краулера
cd crawler
pip install -r requirements.txt

# Запуск краулера для скачивания изображений
python ImageCrawler.py
```

## Команды для работы с Google Gemini

```bash
# Установка зависимостей для интеграции с Gemini
cd gemini-integration
pip install -r requirements.txt

# Настройка API-ключа Gemini
# 1. Скопируйте .env.example в .env
cp .env.example .env

# 2. Отредактируйте файл .env и вставьте ваш API ключ
# GEMINI_API_KEY=ваш_ключ_здесь

# 3. Запуск анализатора изображений с Gemini
python GeminiImageAnalyzer.py
```

## Структура проекта

- `crawler/` - модуль для сбора данных и изображений
- `gemini-integration/` - модуль для анализа изображений с помощью Google Gemini API
- `dataset-labeling/` - модуль для разметки данных (в разработке)
- `yolov11-train/` - модуль для обучения YOLOv11 (в разработке)
- `minio-storage/` - хранение моделей (в разработке)
- `ray-inference/` или `triton-inference/` - сервис для инференса (в разработке)
- `backend/` - FastAPI бэкенд (в разработке)
- `gradio-web/` - веб-интерфейс на Gradio (в разработке)
- `dagster-pipeline/` - пайплайн в Dagster (в разработке)