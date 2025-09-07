#!/bin/bash

echo "🤖 Запуск Telegram бота..."
echo "================================================"

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден! Установите Python3"
    exit 1
fi

# Устанавливаем зависимости
echo "📦 Устанавливаем зависимости..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "⚠️ Ошибка при установке зависимостей, пробуем с --user..."
    python3 -m pip install --user -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Не удалось установить зависимости!"
        exit 1
    fi
fi

# Запускаем бота
echo "🚀 Запускаем бота..."
echo "================================================"
python3 bot.py

