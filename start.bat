@echo off
chcp 65001 >nul
echo Запуск Telegram бота...
echo ================================================

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден! Установите Python с https://python.org
    pause
    exit /b 1
)

REM Устанавливаем зависимости
echo Устанавливаем зависимости...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ВНИМАНИЕ: Ошибка при установке зависимостей, пробуем с --user...
    python -m pip install --user -r requirements.txt
    if errorlevel 1 (
        echo ОШИБКА: Не удалось установить зависимости!
        pause
        exit /b 1
    )
)

REM Запускаем бота
echo Запускаем бота...
echo ================================================
python bot.py

pause
