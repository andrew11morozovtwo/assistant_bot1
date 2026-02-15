# Стандартные библиотеки Python
import csv
import http.client
import io
import logging
import re
import sys
import argparse
from datetime import datetime
from urllib.parse import urlparse

# Сторонние библиотеки
import requests
import telebot
from bs4 import BeautifulSoup
from openai import OpenAI
from PyPDF2 import PdfReader
from newspaper import Article

# Загрузка переменных окружения из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Предупреждение: python-dotenv не установлен. Установите: pip install python-dotenv")
    pass

# Google Colab (опционально)
try:
    from google.colab import userdata
except ImportError:
    # Для локального запуска без Google Colab
    import os
    userdata = type('UserData', (), {
        'get': lambda self, key: os.environ.get(key)
    })()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)

def get_environment_variable(key, required=True):
    """Получает переменную окружения с проверкой"""
    value = os.environ.get(key)
    if required and not value:
        logging.critical(f"Необходимо установить переменную окружения {key}!")
        return None
    return value

# Получение токена Telegram API
API_TOKEN = get_environment_variable('TELEGRAM_BOT_TOKEN')
#API_TOKEN="7168557997:AAGzKOTcg5GfONohwI7UeVSiJETV_-oLzgc"
if not API_TOKEN:
    print("Ошибка: Не найден TELEGRAM_BOT_TOKEN в переменных окружения")
    print("Создайте файл .env с содержимым:")
    print("TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here")
    print("OPENAI_API_KEY=your_openai_api_key_here")
    sys.exit(1)

bot = telebot.TeleBot(API_TOKEN)

# Получение API-ключа OpenAI
OPENAI_API_KEY = get_environment_variable('OPENAI_API_KEY')
#OPENAI_API_KEY="sk-XXXX"
if not OPENAI_API_KEY:
    print("Ошибка: Не найден OPENAI_API_KEY в переменных окружения")
    sys.exit(1)

# Базовый URL для OpenAI / proxyapi (можно переопределить через переменную окружения)
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1")

# Настройка OpenAI
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

# Логируем ключевые параметры подключения к OpenAI / proxyapi (без раскрытия ключа)
logging.info(
    "Инициализация OpenAI клиента: base_url=%s, api_key_prefix=%s***, api_key_len=%d",
    OPENAI_BASE_URL,
    OPENAI_API_KEY[:5],
    len(OPENAI_API_KEY),
)

# Путь к файлу логов (локальный или в контейнере)
file_path = os.environ.get('LOG_FILE_PATH', 'data/telegram_bot_logs.csv')

# Словарь для хранения истории разговора
conversation_history = {}


def extract_text_from_url(url):
    """
    Извлекает текст с веб-страницы по URL.

    Args:
        url (str): Ссылка на страницу.

    Returns:
        str: Извлеченный и очищенный текст или сообщение об ошибке.
    """
    try:
        parsed_url = urlparse(url)

        if not parsed_url.netloc:
            return "Ошибка: Некорректный URL"

        # Убираем трекинговые параметры (utm_*)
        clean_url = url.split("?")[0]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
                "Gecko/20100101 Firefox/128.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        response = requests.get(clean_url, headers=headers, timeout=10)

        if response.status_code == 200:
            # Проверяем что это HTML
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                return f"Неподдерживаемый тип содержимого: {content_type}"

            soup = BeautifulSoup(response.text, 'html.parser')
            cleaned_text = clean_html_text(soup)
            return cleaned_text
        else:
            return f"Ошибка: {response.status_code}"

    except Exception as e:
        return f"Произошла ошибка: {e}"

def extract_main_text_newspaper(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text.strip()
    except Exception as e:
        return f"Ошибка newspaper3k: {e}"

def process_url_in_text(text, bot, chat_id):
    url_match = re.search(r'(http[s]?://[^\s]+)', text)
    if url_match:
        url = url_match.group(0)
        # 1. Пробуем основной способ
        extracted_text = extract_text_from_url(url)
        if extracted_text and not (extracted_text.startswith("Ошибка") or extracted_text.startswith("Произошла ошибка")):
            return f"{text}\n\n{extracted_text}"
        # 2. Если ошибка — пробуем newspaper3k
        main_text = extract_main_text_newspaper(url)
        if main_text and not main_text.startswith("Ошибка"):
            return f"{text}\n\n{main_text}"
        else:
            bot.send_message(chat_id, "Не удалось извлечь текст из ссылки ни одним из способов.")
            return text
    else:
        return text

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    # Инициализация истории разговора для нового чата
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    bot.reply_to(message, "Добро пожаловать в канал 'Это не канал'! Как я могу помочь? Бот версии 14_02_2026 г")

# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text_message(message):
    chat_id = message.chat.id
    user_message = message.text  # Текст сообщения пользователя
    message_type = 'text'  # Указываем тип сообщения как текстовое

    # Проверяем, содержит ли сообщение текст "http"
    if "http" in user_message:
        # Сохраняем исходный текст сообщения
        original_message = user_message

        # Извлекаем первую ссылку из текста
        url_match = re.search(r'(http[s]?://[^\s]+)', user_message)
        if url_match:
            url = url_match.group(0)  # Первая найденная ссылка

            # Пытаемся извлечь текст с веб-страницы
            extracted_text = process_url_in_text(user_message, bot, chat_id)

            if extracted_text:
                # Объединяем текст сообщения с извлеченным текстом
                user_message = extracted_text
                process_message(message, user_message, message_type, chat_id)
            else:
                bot.reply_to(message, "Не удалось извлечь текст из ссылки.")
        else:
            bot.reply_to(message, "Ссылка не найдена в сообщении.")
    else:
        # Если сообщение не содержит "http", обрабатываем его как обычный текст
        process_message(message, user_message, message_type, chat_id)

@bot.message_handler(content_types=['photo'])
def handle_photo_message(message):
    chat_id = message.chat.id
    user_message = message.caption if message.caption else "Фото без подписи"
    message_type = 'photo'

    # Обрабатываем URL в подписи, если он есть
    user_message += process_url_in_text(user_message, bot, chat_id)

    try:
        # Получаем file_id самой большой версии фотографии
        file_id = message.photo[-1].file_id

        # Получаем информацию о файле
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        image_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'

        logging.info(f"URL изображения: {image_url}")  # Логируем URL

    except Exception as e:
        logging.error(f"Ошибка при получении URL изображения из Telegram: {e}")
        user_message += "\nНе удалось получить URL изображения."
        process_message(message, user_message, message_type, chat_id)
        return  # Выходим из функции, чтобы избежать дальнейших ошибок

    try:
        # Запрашиваем описание изображения у OpenAI
        logging.info(
            "Вызов OpenAI chat.completions (описание изображения). Модель=gpt-4o-mini, image_url=%s",
            image_url,
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Что на этом изображении? Дай краткое описание на русском языке."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )

        logging.info(f"Ответ от OpenAI Vision API: {response}")  # Логируем полный ответ

        # Извлекаем описание изображения из ответа OpenAI
        image_description = response.choices[0].message.content

        # Добавляем описание изображения к сообщению пользователя
        user_message += f"\nОписание изображения: {image_description}"

    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI Vision API: {e}")
        user_message += "\nНе удалось получить описание изображения."

    process_message(message, user_message, message_type, chat_id)


@bot.message_handler(content_types=['document'])
def handle_pdf_message(message):
    chat_id = message.chat.id
    user_message = message.caption if message.caption else "PDF документ без подписи"
    message_type = 'document'

    # Проверяем, что это PDF файл
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "Пожалуйста, отправьте PDF файл.")
        return

    # Обрабатываем URL в подписи, если он есть
    user_message += process_url_in_text(user_message, bot, chat_id)

    try:
        # Получаем информацию о файле
        file_info = bot.get_file(message.document.file_id)
        file_path = file_info.file_path
        pdf_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'

        logging.info(f"URL PDF документа: {pdf_url}")  # Логируем URL

    except Exception as e:
        logging.error(f"Ошибка при получении URL PDF документа из Telegram: {e}")
        user_message += "\nНе удалось получить URL PDF документа."
        process_message(message, user_message, message_type, chat_id)
        return

    try:
        # Скачиваем PDF файл
        response = requests.get(pdf_url)
        response.raise_for_status()

        # Читаем PDF файл
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PdfReader(pdf_file)

        # Извлекаем текст из всех страниц
        pdf_text = ""
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text.strip():  # Проверяем, что страница не пустая
                    pdf_text += f"\n--- Страница {page_num} ---\n{page_text}"
            except Exception as e:
                logging.warning(f"Не удалось извлечь текст со страницы {page_num}: {e}")
                continue

        if not pdf_text.strip():
            user_message += "\nНе удалось извлечь текст из PDF документа."
            process_message(message, user_message, message_type, chat_id)
            return

        # Ограничиваем размер текста для API (примерно 4000 токенов)
        if len(pdf_text) > 12000:  # Примерно 4000 токенов
            pdf_text = pdf_text[:12000] + "\n... (текст обрезан из-за ограничений)"

        logging.info(f"Извлеченный текст из PDF: {pdf_text[:500]}...")  # Логируем начало текста

    except Exception as e:
        logging.error(f"Ошибка при обработке PDF файла: {e}")
        user_message += "\nНе удалось обработать PDF файл."
        process_message(message, user_message, message_type, chat_id)
        return

    try:
        # Запрашиваем анализ PDF документа у OpenAI
        logging.info(
            "Вызов OpenAI chat.completions (анализ PDF). Модель=gpt-4o-mini, длина_текста=%d",
            len(pdf_text),
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"""Проанализируй этот PDF документ и дай краткое описание на русском языке.

                    Включи в описание:
                    - Тип документа
                    - Основную тему/содержание
                    - Ключевые пункты
                    - Количество страниц (если видно из текста)

                    Текст документа:
                    {pdf_text}"""
                }
            ],
            max_tokens=500,
        )

        logging.info(f"Ответ от OpenAI для PDF: {response}")  # Логируем полный ответ

        # Извлекаем анализ PDF из ответа OpenAI
        pdf_analysis = response.choices[0].message.content

        # Добавляем анализ PDF к сообщению пользователя
        user_message += f"\n\nАнализ PDF документа:\n{pdf_analysis}"

    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI для анализа PDF: {e}")
        user_message += "\nНе удалось получить анализ PDF документа."

    process_message(message, user_message, message_type, chat_id)

# Обработка сообщений с видео
@bot.message_handler(content_types=['video'])
def handle_video_message(message):
    chat_id = message.chat.id
    user_message = message.caption if message.caption else "Видео без подписи"
    message_type = 'video'

    # Обрабатываем URL в подписи, если он есть
    user_message += process_url_in_text(user_message, bot, chat_id)

    process_message(message, user_message, message_type, chat_id)


# Обработка голосовых сообщений
@bot.message_handler(content_types=['voice'])
def handle_voice_message(message):
    chat_id = message.chat.id
    message_type = 'voice'

    try:
        # Получаем информацию о файле
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'

        # Скачиваем файл
        response = requests.get(file_url)
        response.raise_for_status()  # Проверяем на ошибки

        # Открываем файл как бинарный
        audio_file = io.BytesIO(response.content)

        # Транскрибируем аудио
        logging.info(
            "Вызов OpenAI audio.transcriptions.create (voice). Модель=whisper-1, file_path=%s, размер_байт=%d",
            file_path,
            len(response.content),
        )
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=(file_path, audio_file)  # Передаем имя файла и объект BytesIO
        )

        # Получаем транскрибированный текст
        transcribed_text = transcription.text

        # Формируем сообщение пользователю: сначала подпись, потом транскрипция
        user_message = message.caption if message.caption else ""  # Получаем подпись
        user_message = process_url_in_text(user_message, bot, chat_id)  # Обрабатываем URL в подписи, если он есть
        user_message += f"\nТранскрипция аудио: {transcribed_text}"  # Добавляем транскрипцию

    except Exception as e:
        logging.error(f"Ошибка при транскрибации аудио: {e}")
        bot.reply_to(message, "Произошла ошибка при транскрибации аудио.")

    process_message(message, user_message, message_type, chat_id)


# Обработка аудио сообщений
@bot.message_handler(content_types=['audio'])
def handle_audio_message(message):
    chat_id = message.chat.id
    message_type = 'audio'

    try:
        # Получаем информацию о файле
        file_id = message.audio.file_id  # Изменено с message.voice.file_id на message.audio.file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'

        # Скачиваем файл
        response = requests.get(file_url)
        response.raise_for_status()  # Проверяем на ошибки

        # Открываем файл как бинарный
        audio_file = io.BytesIO(response.content)

        # Транскрибируем аудио
        logging.info(
            "Вызов OpenAI audio.transcriptions.create (audio). Модель=whisper-1, file_path=%s, размер_байт=%d",
            file_path,
            len(response.content),
        )
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=(file_path, audio_file)  # Передаем имя файла и объект BytesIO
        )

        # Получаем транскрибированный текст
        transcribed_text = transcription.text

         # Формируем сообщение пользователю: сначала подпись, потом транскрипция
        user_message = message.caption if message.caption else ""  # Получаем подпись
        user_message = process_url_in_text(user_message, bot, chat_id) # Обрабатываем URL в подписи, если он есть
        user_message += f"\nТранскрипция аудио: {transcribed_text}"  # Добавляем транскрипцию

    except Exception as e:
        logging.error(f"Ошибка при транскрибации аудио: {e}")
        bot.reply_to(message, "Произошла ошибка при транскрибации аудио.")

    process_message(message, user_message, message_type, chat_id)

# Обработка опросов
@bot.message_handler(content_types=['poll'])
def handle_poll_message(message):
    chat_id = message.chat.id
    user_message = f"Опрос: {message.poll.question}"
    message_type = 'poll'
    process_message(message, user_message, message_type, chat_id)

# Функция для инициализации файла (создаем файл и пишем заголовки, если он не существует)
def initialize_log_file():
    # Создаем директорию для файла логов, если она не существует
    log_dir = os.path.dirname(file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['chat_id', 'datetime', 'message', 'message_type', 'ai_response'])

# Функция для записи данных в файл
def log_to_file(chat_id, user_message, message_type, ai_response):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Текущее время
    with open(file_path, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([chat_id, current_time, user_message, message_type, ai_response])

# Общая функция для обработки сообщений
def process_message(message, user_message, message_type, chat_id):
    # Проверяем, существует ли история для данного chat_id
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    # Добавляем сообщение пользователя в историю разговора
    conversation_history[chat_id].append({"role": "user", "content": user_message})
    logging.info(f"Получено сообщение от пользователя: {user_message} (Тип: {message_type})")
    # Запрос к OpenAI с историей разговора
    try:
        logging.info(
            "Вызов OpenAI chat.completions (основной ответ). Модель=gpt-3.5-turbo-1106, длина_истории=%d, длина_сообщения=%d",
            len(conversation_history[chat_id]),
            len(user_message),
        )
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=conversation_history[chat_id] + [
                {"role": "system", "content": (
                    "Вы бот-администратор в телеграм-канале 'Это не канал'. Ваша задача — пересказывать на русском языке "
                    "подписчикам материалы, присылаемые в канал. Формируйте краткий (не более 3000 знаков) и интересный пересказ, "
                    "ориентируясь на следующие принципы:\n\n"
                    "1. Прочитайте пост. Если в посте указана ссылка, предположите, что она содержит дополнительную информацию. "
                    "Попробуйте дать пересказ, основываясь на теме, изложенной в посте, а также возможных контекстах.\n"
                    "2. Пересказ оформляйте структурно:\n"
                    "- Введение: кратко объясните, о чем материал и почему он важен.\n"
                    "- Основная часть: изложите ключевые моменты материала простым языком, подчеркивая суть. Разделяйте текст на абзацы.\n"
                    "- Заключение: сделайте выводы, предложите рекомендации или задайте вопрос для вовлечения подписчиков.\n"
                    "3. Если пост содержит только ссылку, составьте предположительный пересказ на основе общего контекста и доступной информации. "
                    "Укажите, что пересказ основан на интерпретации.\n"
                    "4. Указывайте источник информации в конце текста (например: 'Источник: ссылка из поста').\n\n"
                    "Общайтесь с читателями вежливо, от мужского лица, используя 'Вы'.\n\n"
                    "Включайте эмодзи для акцентирования ключевых моментов, таких как:\n"
                    "- 🔍 для выделения важных деталей,\n"
                    "- 📌 для ключевых тезисов,\n"
                    "- 🌟 для рекомендаций.\n\n"
                    "Следите за тем, чтобы текст был легко читаем на русском языке и не перегружен эмодзи. Старайтесь создавать увлекательные посты, чтобы подписчики захотели прочитать оригинал."
                )},
                {"role": "user", "content": user_message}
            ]
        )
        # Получаем ответ от AI
        ai_response = chat_completion.choices[0].message.content
        bot.reply_to(message, ai_response)

        # Логирование данных в файл
        log_to_file(chat_id, user_message, message_type, ai_response)

        # Добавляем ответ AI в историю разговора
        conversation_history[chat_id].append({"role": "assistant", "content": ai_response})
    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI: {e}")
        bot.reply_to(message, "Извините, произошла ошибка при обработке вашего запроса.")

def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Telegram Bot для канала "Это не канал"')
    parser.add_argument('--debug', action='store_true', help='Включить режим отладки')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Уровень логирования')
    parser.add_argument('--log-file', default='logs/bot.log', help='Файл для логов')
    return parser.parse_args()

def main():
    """Основная функция запуска бота"""
    args = parse_arguments()
    
    # Настройка логирования в зависимости от аргументов
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Проверка переменных окружения
    if not API_TOKEN or not OPENAI_API_KEY:
        print("Ошибка: Не все необходимые переменные окружения установлены")
        print("Создайте файл .env в корневой папке проекта:")
        print("TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here")
        print("OPENAI_API_KEY=your_openai_api_key_here")
        sys.exit(1)
    
    try:
        # Инициализация файла логов
        initialize_log_file()
        
        print("🤖 Запуск Telegram бота...")
        print(f"📝 Логи будут записываться в: logs/bot.log")
        print(f"📊 Данные будут сохраняться в: {file_path}")
        print("🔄 Бот запущен и ожидает сообщения...")
        print("Для остановки нажмите Ctrl+C")
        
        # Запуск бота
        bot.polling(none_stop=True, timeout=60)
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        print(f"❌ Ошибка запуска бота: {e}")
        sys.exit(1)

# Запуск бота
if __name__ == '__main__':
    main()
