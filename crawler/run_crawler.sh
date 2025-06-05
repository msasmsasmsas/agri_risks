#!/bin/bash

echo "Запуск краулера изображений для сельскохозяйственных рисков"
echo ""

# Активация виртуальной среды, если она существует
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
fi

# Проверка установленных зависимостей
pip install -r requirements.txt

# Запуск краулера с параметрами
python ImageCrawler.py --engine both --max-images 10 --delay 2.0

echo ""
echo "Краулер завершил работу"
