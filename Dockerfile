# 1. Базовый образ
FROM python:3.11-slim

# 2. Установка системных зависимостей (для lxml и других)
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Создание рабочего каталога
WORKDIR /app

# 4. Копирование зависимостей и установка pip-пакетов
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копирование исходного кода
COPY bot.py .
COPY run_bot.py .
# Если нужны другие файлы — добавьте COPY

# 7. Создание папок для логов и данных
RUN mkdir -p /app/logs /app/data

# 8. Открытие порта (если нужно)
EXPOSE 8080

# 9. Стартовая команда
CMD ["python", "bot.py"]
