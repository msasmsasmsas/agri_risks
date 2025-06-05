@echo off
echo Конвертирование WEBP изображений в формат JPG
echo.

REM Активация виртуальной среды, если она существует
if exist ..\venv\Scripts\activate.bat (
    call ..\venv\Scripts\activate.bat
)

REM Запуск конвертера
python convert_webp.py --directory download --fix-names

echo.
echo Конвертер завершил работу
echo Нажмите любую клавишу для выхода...
pause > nul
