@echo off
echo 🐳 Запуск Telegram бота в Docker...

REM Проверяем наличие Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker не установлен!
    echo Установите Docker с https://docker.com
    pause
    exit /b 1
)

REM Проверяем наличие docker-compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose не установлен!
    echo Установите Docker Compose
    pause
    exit /b 1
)

REM Проверяем наличие файла .env
if not exist ".env" (
    echo ❌ Файл .env не найден!
    echo Создайте файл .env с токенами:
    echo TELEGRAM_BOT_TOKEN=ваш_токен_бота
    echo OPENAI_API_KEY=ваш_ключ_openai
    pause
    exit /b 1
)

REM Создаем директории для логов и данных
if not exist "logs" mkdir logs
if not exist "data" mkdir data

echo 🔨 Сборка Docker образа...
docker-compose build

echo 🚀 Запуск контейнера...
docker-compose up -d

echo ✅ Бот запущен в контейнере!
echo 📝 Логи: docker-compose logs -f
echo 🛑 Остановка: docker-compose down

pause
