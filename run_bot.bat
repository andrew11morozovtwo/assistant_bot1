@echo off
echo 🤖 Запуск Telegram бота...
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python с https://python.org
    pause
    exit /b 1
)

REM Проверяем наличие файла .env
if not exist ".env" (
    echo ❌ Файл .env не найден!
    echo Создайте файл .env в корневой папке проекта
    echo Скопируйте содержимое из env.example и заполните ваши токены
    pause
    exit /b 1
)

REM Устанавливаем зависимости если нужно
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

echo 🔧 Активация виртуального окружения...
call venv\Scripts\activate.bat

echo 📦 Установка зависимостей...
pip install -r requirements.txt

echo 🚀 Запуск бота...
python bot.py

pause
