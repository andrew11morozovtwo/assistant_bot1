# Используем Python 3.11 slim образ для меньшего размера
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для безопасности
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY bot.py .
COPY run_bot.py .

# Копируем .env файл из корня проекта
COPY .env .env

# Создаем необходимые директории
RUN mkdir -p /app/logs /app/data && \
    chown -R botuser:botuser /app

# Переключаемся на пользователя botuser
USER botuser

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Команда запуска
CMD ["python", "-m", "bot"]
