# Стандартные библиотеки Python
import csv
import http.client
import io
import logging
import os
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

# Проверяем наличие необходимых модулей
try:
    import requests
    import telebot
    from bs4 import BeautifulSoup
    from openai import OpenAI
    from PyPDF2 import PdfReader
    from dotenv import load_dotenv
    # Google Gemini official client (proxy-compatible)
    from google import genai as google_genai
    import cv2
    import base64
    import tempfile
    import os
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("💡 Установите зависимости: pip install -r requirements.txt")
    sys.exit(1)

# Загружаем переменные окружения из файла config.env
load_dotenv('config.env')

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение токена Telegram API из переменной окружения
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not API_TOKEN:
    logging.critical("Необходимо установить переменную окружения TELEGRAM_BOT_TOKEN в файле config.env!")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)

# Получение API-ключа OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.critical("Необходимо установить переменную окружения OPENAI_API_KEY в файле config.env!")
    exit(1)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.proxyapi.ru/openai/v1",
)

# Получение API-ключа Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.warning("GEMINI_API_KEY не найден в config.env! Анализ видео будет недоступен.")

gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = google_genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"base_url": "https://api.proxyapi.ru/google"}
        )
    except Exception as e:
        logging.warning(f"Не удалось инициализировать Gemini клиент: {e}")
        gemini_client = None

# Путь к файлу логов (локальная папка)
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
file_path = os.path.join(logs_dir, 'telegram_bot_logs.csv')

# Словарь для хранения истории разговора
conversation_history = {}

def process_url_in_text(text, bot, chat_id):
    """
    Ищет URL в тексте и, если находит, извлекает текст с веб-страницы.

    Args:
        text (str): Текст для поиска URL.
        bot (telebot.TeleBot): Экземпляр бота.
        chat_id (int): ID чата.

    Returns:
        str: Объединенный текст (исходный текст + текст с веб-страницы) или исходный текст, если URL не найден.
    """
    url_match = re.search(r'(http[s]?://[^\s]+)', text)
    if url_match:
        url = url_match.group(0)  # Первая найденная ссылка
        logging.info(f"Извлекаем текст из URL: {url}")
        
        extracted_text = extract_text_from_url(url)

        if extracted_text and not extracted_text.startswith("Ошибка"):
            logging.info(f"Текст успешно извлечен, длина: {len(extracted_text)} символов")
            return f"{text}\n\n{extracted_text}"
        else:
            error_msg = f"Не удалось извлечь текст из ссылки: {extracted_text}"
            logging.warning(error_msg)
            try:
                bot.send_message(chat_id, error_msg)
            except Exception:
                pass
            return text
    else:
        return text

# Функция для извлечения текста из URL
def extract_text_from_url(url):
    try:
        # Проверяем URL
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            return "Ошибка: Некорректный URL"

        # Настройки для запроса
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        # Делаем запрос с таймаутом и сессией
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=15, allow_redirects=True)
        response.raise_for_status()  # Проверяем на ошибки HTTP

        # Парсим HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Удаляем ненужные элементы
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Извлекаем текст
        text_content = soup.get_text()
        
        # Очищаем текст
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Ограничиваем размер текста
        if len(cleaned_text) > 8000:
            cleaned_text = cleaned_text[:8000] + "\n... (текст обрезан из-за ограничений)"
        
        return cleaned_text

    except requests.exceptions.Timeout:
        return "Ошибка: Превышено время ожидания при загрузке страницы"
    except requests.exceptions.ConnectionError:
        return "Ошибка: Не удалось подключиться к серверу"
    except requests.exceptions.HTTPError as e:
        return f"Ошибка HTTP: {e.response.status_code}"
    except Exception as e:
        return f"Произошла ошибка: {e}"

def extract_video_frames(video_path, max_frames=5):
    """
    Извлекает кадры из видео для анализа
    
    Args:
        video_path (str): Путь к видеофайлу
        max_frames (int): Максимальное количество кадров для извлечения
    
    Returns:
        list: Список кадров в формате base64
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
        
        frames = []
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Выбираем кадры равномерно по времени
        if frame_count > max_frames:
            step = frame_count // max_frames
        else:
            step = 1
        
        frame_number = 0
        extracted_count = 0
        
        while extracted_count < max_frames and frame_number < frame_count:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret:
                # Конвертируем BGR в RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Кодируем в JPEG
                _, buffer = cv2.imencode('.jpg', frame_rgb)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                frames.append(frame_base64)
                extracted_count += 1
            
            frame_number += step
        
        cap.release()
        return frames
        
    except Exception as e:
        logging.error(f"Ошибка при извлечении кадров из видео: {e}")
        return []

def analyze_video_with_gemini(video_frames=None, user_message="", video_path=None):
    """
    Анализирует видео с помощью Gemini 1.5 Pro, если доступно.
    Если нет доступа — гибридный вариант (Whisper + сцены через ffmpeg/кадры).

    Args:
        video_frames (list): Список кадров (используется только в fallback).
        user_message (str): Сообщение пользователя.
        video_path (str): Путь к локальному видеофайлу.
    Returns:
        str: Описание видео.
    """
    if not gemini_client:
        return "Анализ видео недоступен: Gemini клиент не инициализирован."

    try:
        # Попробуем использовать Gemini 1.5 Pro напрямую
        logging.info("Пробуем отправить видео в Gemini 1.5 Pro...")
        if video_path:
            try:
                with open(video_path, 'rb') as vf:
                    response = gemini_client.models.generate_content(
                        model="gemini-1.5-pro",
                        contents=[
                            google_genai.types.Part.from_bytes(
                                data=vf.read(),
                                mime_type="video/mp4"
                            ),
                            f"Опиши это видео подробно на русском языке. Пользователь написал: {user_message}"
                        ]
                    )
                if hasattr(response, 'text'):
                    return response.text
                return str(response)
            except Exception as e:
                logging.warning(f"Не удалось использовать Gemini 1.5 Pro напрямую: {e}")

        # --- Fallback ---
        logging.info("Используем гибридный анализ (Whisper + сцены).")

        transcript_text = ""
        if video_path:
            try:
                with open(video_path, 'rb') as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=(os.path.basename(video_path), audio_file)
                    )
                transcript_text = transcription.text
                logging.info(f"Транскрипция получена: {len(transcript_text)} символов")
            except Exception as e:
                logging.warning(f"Не удалось транскрибировать аудио: {e}")

        frames_for_summary = video_frames or []
        if video_path and not frames_for_summary:
            frames_for_summary = extract_video_frames(video_path, max_frames=5)

        description_parts = []
        if frames_for_summary:
            description_parts.append("Извлечены ключевые кадры, на них видно объекты и действия.")
        if transcript_text:
            description_parts.append(f"Транскрипция речи/звука: {transcript_text}")

        fallback_prompt = f"""Проанализируй видео на основе доступных данных.
        Сообщение пользователя: {user_message}
        Данные:
{os.linesep.join(description_parts)}
        Составь связный пересказ видео: сюжет, объекты, действия, выводы. Отвечай на русском языке."""

        chat_completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": fallback_prompt}],
            max_tokens=700,
        )
        return chat_completion.choices[0].message.content

    except Exception as e:
        logging.error(f"Ошибка при анализе видео: {e}")
        return f"Ошибка при анализе видео: {e}"

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    # Инициализация истории разговора для нового чата
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    bot.reply_to(message, "Добро пожаловать в канал 'Это не канал'! Как я могу помочь? Бот версии 21_01_2025 г")

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
        import re
        url_match = re.search(r'(http[s]?://[^\s]+)', user_message)
        if url_match:
            url = url_match.group(0)  # Первая найденная ссылка

            # Пытаемся извлечь текст с веб-страницы
            extracted_text = extract_text_from_url(url)

            if extracted_text:
                # Объединяем текст сообщения с извлеченным текстом
                user_message = f"{original_message}\n\n{extracted_text}"
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
    user_message = message.caption if message.caption else "Документ"
    message_type = 'document'

    # Если документ — это видео (многие клиенты отправляют mp4 как document)
    mime_type = getattr(message.document, 'mime_type', '') or ''
    if mime_type.startswith('video/') or message.document.file_name.lower().endswith(('.mp4', '.mov', '.mkv', '.webm')):
        # Проксируем обработку как видео
        try:
            # Сначала проверяем размер из самого message, не запрашивая getFile
            file_size = getattr(message.document, 'file_size', 0)
            if file_size > 20 * 1024 * 1024:
                bot.send_message(chat_id,
                    f"⚠️ Видео слишком большое ({round(file_size/1024/1024,1)} MB). "
                    "Telegram API не позволяет скачать файлы больше 20 MB. "
                    "Пожалуйста, отправьте укороченную или сжатую версию.")
                return
            # Получаем файл
            file_info = bot.get_file(message.document.file_id)
            file_path = file_info.file_path
            video_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'

            # Скачиваем во временный файл
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        temp_file.write(chunk)
                temp_video_path = temp_file.name

            try:
                video_frames = extract_video_frames(temp_video_path, max_frames=5)
                if video_frames:
                    video_analysis = analyze_video_with_gemini(video_frames, user_message)
                    first_frame = base64.b64decode(video_frames[0])
                    bio = io.BytesIO(first_frame); bio.name = 'frame.jpg'
                    bot.send_photo(chat_id, photo=bio, caption=video_analysis[:1024])
                    process_message(message, f"{user_message}\n\nАнализ видео (document):\n{video_analysis}", message_type, chat_id)
                else:
                    bot.send_message(chat_id, "Не удалось извлечь кадры из видео-документа для анализа.")
            finally:
                try:
                    os.unlink(temp_video_path)
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Ошибка при обработке видео-документа: {e}")
            bot.send_message(chat_id, "Ошибка при обработке видео-документа.")
        return

    # Иначе — ожидаем PDF
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
    user_message = process_url_in_text(user_message, bot, chat_id)

    try:
        # Быстрая проверка лимита размера: у video обычно есть поле file_size
        video_size = getattr(message.video, 'file_size', 0)
        if video_size > 20 * 1024 * 1024:
            bot.send_message(chat_id,
                f"⚠️ Видео слишком большое ({round(video_size/1024/1024,1)} MB). "
                "Telegram API не позволяет скачать файлы больше 20 MB. "
                "Пожалуйста, отправьте укороченную или сжатую версию.")
            return

        # Получаем информацию о файле
        file_id = message.video.file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'
        logging.info(f"URL видео: {file_url}")

        # Скачиваем видео во временный файл
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    temp_file.write(chunk)
            temp_video_path = temp_file.name

        try:
            # Анализируем через новую функцию (первично Gemini 1.5 Pro, иначе гибрид)
            analysis = analyze_video_with_gemini(video_frames=None, user_message=user_message, video_path=temp_video_path)
            user_message += f"\n\nАнализ видео:\n{analysis}"
        finally:
            try:
                os.unlink(temp_video_path)
            except Exception:
                pass

    except Exception as e:
        logging.error(f"Ошибка при обработке видео: {e}")
        user_message += f"\nОшибка при обработке видео: {e}"

    process_message(message, user_message, message_type, chat_id)


# ===== Обработчики постов в канале (channel_post) =====
# Многие сообщения в каналах приходят как channel_post, поэтому проксируем их в те же обработчики

@bot.channel_post_handler(content_types=['text'])
def channel_post_text(message):
    handle_text_message(message)

@bot.channel_post_handler(content_types=['photo'])
def channel_post_photo(message):
    handle_photo_message(message)

@bot.channel_post_handler(content_types=['document'])
def channel_post_document(message):
    handle_pdf_message(message)

@bot.channel_post_handler(content_types=['video'])
def channel_post_video(message):
    handle_video_message(message)

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

# Запуск бота
if __name__ == '__main__':
    initialize_log_file()  # Инициализация файла логов
    try:
        # Сбрасываем вебхук, чтобы избежать конфликта с polling
        bot.remove_webhook()
    except Exception:
        pass
    # Явно указываем список типов апдейтов, чтобы бот получал посты из каналов
    allowed_updates = [
        "message",
        "edited_message",
        "channel_post",
        "edited_channel_post",
    ]
    # Запускаем единичный polling и пропускаем накопившиеся апдейты
    bot.infinity_polling(skip_pending=True, timeout=20, allowed_updates=allowed_updates)
