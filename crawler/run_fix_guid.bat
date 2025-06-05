@echo off
echo Исправление GUID в именах файлов...
echo.

REM Активация виртуальной среды, если она существует
if exist ..\venv\Scripts\activate.bat (
    call ..\venv\Scripts\activate.bat
)

REM Запуск скрипта исправления GUID
python fix_guid.py --directory download/images

echo.
echo Исправление GUID завершено.
echo Нажмите любую клавишу для выхода...
pause > nul
