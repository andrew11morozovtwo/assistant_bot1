# 🐳 Запуск Telegram бота в Docker

## Предварительные требования

1. **Установите Docker**: https://docker.com
2. **Установите Docker Compose** (обычно идет с Docker Desktop)

## Быстрый запуск

### Для Windows:
```bash
# Двойной клик на файл
docker-run.bat
```

### Для Linux/Mac:
```bash
# Сделайте скрипт исполняемым
chmod +x docker-run.sh

# Запустите
./docker-run.sh
```

### Ручной запуск:
```bash
# Сборка образа
docker-compose build

# Запуск контейнера
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

## Настройка

1. **Создайте файл `.env`** с токенами:
   ```env
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   OPENAI_API_KEY=ваш_ключ_openai
   LOG_FILE_PATH=/app/data/telegram_bot_logs.csv
   ```

2. **Создайте директории** (если не созданы автоматически):
   ```bash
   mkdir logs data
   ```

## Структура проекта

```
it_is_not_chanal/
├── bot.py                    # Основной файл бота
├── run_bot.py               # Скрипт запуска
├── requirements.txt          # Зависимости
├── Dockerfile               # Конфигурация Docker
├── docker-compose.yml       # Docker Compose
├── .dockerignore           # Исключения для Docker
├── docker-run.sh           # Скрипт запуска (Linux/Mac)
├── docker-run.bat          # Скрипт запуска (Windows)
├── .env                    # Переменные окружения
├── logs/                   # Логи (создается автоматически)
└── data/                   # Данные (создается автоматически)
```

## Команды Docker

### Основные команды:
```bash
# Сборка образа
docker-compose build

# Запуск в фоне
docker-compose up -d

# Запуск с выводом логов
docker-compose up

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f

# Перезапуск
docker-compose restart

# Обновление образа
docker-compose pull
```

### Полезные команды:
```bash
# Проверить статус контейнеров
docker-compose ps

# Войти в контейнер
docker-compose exec telegram-bot bash

# Просмотреть использование ресурсов
docker stats telegram-bot

# Очистить неиспользуемые образы
docker system prune
```

## Переменные окружения

В файле `.env` можно настроить:

```env
# Обязательные
TELEGRAM_BOT_TOKEN=ваш_токен_бота
OPENAI_API_KEY=ваш_ключ_openai

# Опциональные
LOG_FILE_PATH=/app/data/telegram_bot_logs.csv
MAX_PDF_TEXT_LENGTH=12000
MAX_AI_RESPONSE_LENGTH=3000
```

## Логи и данные

- **Логи контейнера**: `docker-compose logs -f`
- **Логи бота**: `./logs/bot.log`
- **Данные чатов**: `./data/telegram_bot_logs.csv`

## Безопасность

- Контейнер запускается от непривилегированного пользователя
- Токены передаются через переменные окружения
- Логи и данные сохраняются в volume

## Устранение проблем

### Ошибка "Docker не установлен"
- Установите Docker Desktop с https://docker.com

### Ошибка "Docker Compose не установлен"
- Docker Compose обычно идет с Docker Desktop
- Или установите отдельно: `pip install docker-compose`

### Ошибка "Файл .env не найден"
- Создайте файл `.env` с токенами

### Ошибка сборки образа
- Проверьте подключение к интернету
- Попробуйте: `docker system prune`

### Контейнер не запускается
- Проверьте логи: `docker-compose logs`
- Убедитесь, что токены правильные
