@echo off
echo Конвертер WEBP в JPG
echo.

REM Активация виртуальной среды, если она существует
if exist ..\venv\Scripts\activate.bat (
    call ..\venv\Scripts\activate.bat
)

REM Запуск конвертера
python convert_webp_to_jpg.py --directory download/images --rename

echo.
echo Конвертация завершена
echo Нажмите любую клавишу для выхода...
pause > nul
