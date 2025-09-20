#!/bin/bash

# Скрипт для запуска Telegram бота в Docker

echo "🐳 Запуск Telegram бота в Docker..."

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "Установите Docker с https://docker.com"
    exit 1
fi

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен!"
    echo "Установите Docker Compose"
    exit 1
fi

# Проверяем наличие файла .env
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env с токенами:"
    echo "TELEGRAM_BOT_TOKEN=ваш_токен_бота"
    echo "OPENAI_API_KEY=ваш_ключ_openai"
    exit 1
fi

# Создаем директории для логов и данных
mkdir -p logs data

echo "🔨 Сборка Docker образа..."
docker-compose build

echo "🚀 Запуск контейнера..."
docker-compose up -d

echo "✅ Бот запущен в контейнере!"
echo "📝 Логи: docker-compose logs -f"
echo "🛑 Остановка: docker-compose down"
