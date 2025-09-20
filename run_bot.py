#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота с проверкой настроек
"""

import os
import sys
import subprocess

def check_env_file():
    """Проверяет наличие файла .env"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("Создайте файл .env в корневой папке проекта")
        print("Скопируйте содержимое из env.example и заполните ваши токены")
        return False
    return True

def check_dependencies():
    """Проверяет установленные зависимости"""
    try:
        import telebot
        import openai
        import requests
        import bs4
        import PyPDF2
        try:
            from dotenv import load_dotenv
        except ImportError:
            print("⚠️  python-dotenv не установлен. Установите: pip install python-dotenv")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        return False

def main():
    """Основная функция"""
    print("🤖 Проверка настроек Telegram бота...")
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Проверяем файл .env
    if not check_env_file():
        sys.exit(1)
    
    print("✅ Все проверки пройдены!")
    print("🚀 Запуск бота...")
    print()
    
    # Запускаем бота
    try:
        subprocess.run([sys.executable, "bot.py"] + sys.argv[1:], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
