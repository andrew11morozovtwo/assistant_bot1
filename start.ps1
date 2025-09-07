# PowerShell скрипт для запуска Telegram бота
Write-Host "🤖 Запуск Telegram бота..." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Yellow

# Проверяем наличие Python
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python не найден"
    }
    Write-Host "✅ Python найден: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python не найден! Установите Python с https://python.org" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Устанавливаем зависимости
Write-Host "📦 Устанавливаем зависимости..." -ForegroundColor Cyan
try {
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ Ошибка при установке зависимостей, пробуем с --user..." -ForegroundColor Yellow
        python -m pip install --user -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Не удалось установить зависимости"
        }
    }
    Write-Host "✅ Зависимости установлены успешно!" -ForegroundColor Green
} catch {
    Write-Host "❌ Не удалось установить зависимости!" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Запускаем бота
Write-Host "🚀 Запускаем бота..." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Yellow
python bot.py

Read-Host "Нажмите Enter для выхода"

