# Модуль интеграции с Google Gemini
# Модуль интеграции с Google Gemini

## Настройка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл .env на основе .env.example:
```bash
cp .env.example .env
```

3. Получите API ключ на [Google AI Studio](https://ai.google.dev/)

4. Отредактируйте .env файл и добавьте ваш API ключ:
```
GEMINI_API_KEY=ваш_ключ_здесь
```

## Запуск

### Анализ отдельных изображений
```bash
python GeminiImageAnalyzer.py
```

### Запуск бенчмарка
```bash
python GeminiApiBenchmark.py
```

## Примечание по использованию

Модуль `gemini_client.py` содержит класс `GeminiClient`, который можно импортировать в другие скрипты:

```python
from gemini_client import GeminiClient

client = GeminiClient()
result = client.analyze_image("path/to/image.jpg")
print(result)
```
Модуль для распознавания рисков сельскохозяйственных культур с помощью Google Gemini API.

## Настройка

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Получите API ключ на [Google AI Studio](https://ai.google.dev/)

3. Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

4. Отредактируйте файл `.env` и добавьте ваш API ключ:

```
GEMINI_API_KEY=ваш_ключ_gemini_api
```

## Использование

### Анализ изображений

```bash
python GeminiImageAnalyzer.py
```

### Запуск бенчмарка производительности

```bash
python GeminiApiBenchmark.py
```

## Примеры кода

```python
from GeminiImageAnalyzer import GeminiClient

# Клиент автоматически загрузит API ключ из .env файла
client = GeminiClient()

# Анализ изображения
result = client.analyze_image("path/to/image.jpg")
print(result)
```
