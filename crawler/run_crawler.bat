@echo off
echo Запуск краулера изображений для сельскохозяйственных рисков
echo.

REM Активация виртуальной среды, если она существует
if exist ..\venv\Scripts\activate.bat (
    call ..\venv\Scripts\activate.bat
)

REM Проверка установленных зависимостей
pip install -r requirements.txt

REM Запуск краулера с параметрами
python ImageCrawler.py --engine both --max-images 500 --delay 2.0

echo.
echo Краулер завершил работу
echo Нажмите любую клавишу для выхода...
pause > nul
