#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота
Проверяет наличие необходимых файлов и зависимостей перед запуском
"""

import os
import sys
import subprocess

def install_package(package):
    """Устанавливает пакет через pip с несколькими попытками"""
    commands = [
        [sys.executable, '-m', 'pip', 'install', package],
        [sys.executable, '-m', 'pip', 'install', '--user', package],
        [sys.executable, '-m', 'pip', 'install', '--upgrade', package],
    ]
    
    for i, cmd in enumerate(commands, 1):
        try:
            print(f"Попытка {i}: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            print(f"{package} установлен успешно")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Попытка {i} не удалась: {e}")
            if i == len(commands):
                print(f"ОШИБКА: Все попытки установки {package} не удались")
                return False
            continue
    return False

def check_requirements():
    """Проверяет наличие файла requirements.txt и устанавливает зависимости"""
    if not os.path.exists('requirements.txt'):
        print("ОШИБКА: Файл requirements.txt не найден!")
        return False
    
    print("Проверяем и устанавливаем зависимости...")
    print(f"Python версия: {sys.version}")
    print(f"Python путь: {sys.executable}")
    print()
    
    # Список пакетов для установки
    packages = [
        'requests',
        'pyTelegramBotAPI', 
        'beautifulsoup4',
        'openai',
        'PyPDF2',
        'python-dotenv',
        'google-generativeai',
        'opencv-python'
    ]
    
    print("Устанавливаем зависимости...")
    failed_packages = []
    
    for package in packages:
        print(f"Устанавливаем {package}...")
        if not install_package(package):
            failed_packages.append(package)
    
    if failed_packages:
        print(f"ВНИМАНИЕ: Не удалось установить: {', '.join(failed_packages)}")
        print("Совет: Попробуйте запустить от имени администратора")
        return False
    
    print("Все зависимости установлены!")
    
    # Проверяем импорты
    print("Проверяем импорты...")
    try:
        import requests
        print("requests импортирован успешно!")
        import telebot
        print("telebot импортирован успешно!")
        from bs4 import BeautifulSoup
        print("beautifulsoup4 импортирован успешно!")
        from openai import OpenAI
        print("openai импортирован успешно!")
        from PyPDF2 import PdfReader
        print("PyPDF2 импортирован успешно!")
        from dotenv import load_dotenv
        print("python-dotenv импортирован успешно!")
        import google.generativeai as genai
        print("google-generativeai импортирован успешно!")
        import cv2
        print("opencv-python импортирован успешно!")
        print("Все модули импортированы успешно!")
    except ImportError as e:
        print(f"ОШИБКА импорта: {e}")
        print("Совет: Попробуйте перезапустить скрипт или перезагрузить компьютер")
        return False
    
    return True

def check_config():
    """Проверяет наличие файла конфигурации"""
    if not os.path.exists('config.env'):
        print("ОШИБКА: Файл config.env не найден!")
        print("Создайте файл config.env и добавьте ваши токены:")
        print("   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here")
        print("   OPENAI_API_KEY=your_openai_api_key_here")
        return False
    
    print("Файл конфигурации найден!")
    return True

def main():
    """Основная функция"""
    print("Запуск Telegram бота...")
    print("=" * 50)
    
    # Проверяем конфигурацию
    if not check_config():
        return
    
    # Проверяем и устанавливаем зависимости
    if not check_requirements():
        return
    
    print("Запускаем бота...")
    print("=" * 50)
    
    # Запускаем основной файл бота
    try:
        import bot
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"ОШИБКА при запуске бота: {e}")

if __name__ == "__main__":
    main()
