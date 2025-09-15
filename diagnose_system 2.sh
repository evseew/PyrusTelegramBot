#!/bin/bash

# 🔍 ПОЛНАЯ ДИАГНОСТИКА PYRUS TELEGRAM BOT СИСТЕМЫ
# Использование: ./diagnose_system.sh

set -e

echo "🔍 ДИАГНОСТИКА PYRUS TELEGRAM BOT СИСТЕМЫ"
echo "=========================================="
echo "Время: $(date)"
echo "Сервер: $(hostname)"
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для красивого вывода
success() { echo -e "${GREEN}✅ $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
info() { echo -e "${BLUE}ℹ️ $1${NC}"; }

# Счетчики
ERRORS=0
WARNINGS=0

# Функция для проверки и записи ошибок
check_result() {
    if [ $1 -eq 0 ]; then
        success "$2"
    else
        error "$2"
        ((ERRORS++))
    fi
}

check_warning() {
    if [ $1 -eq 0 ]; then
        success "$2"
    else
        warning "$2"
        ((WARNINGS++))
    fi
}

echo "📋 1. ПРОВЕРКА ОКРУЖЕНИЯ"
echo "========================"

# Проверка Python
echo -n "Проверка Python 3... "
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    success "Python установлен: $PYTHON_VERSION"
else
    error "Python 3 не найден!"
    ((ERRORS++))
fi

# Проверка pip
echo -n "Проверка pip3... "
if command -v pip3 >/dev/null 2>&1; then
    PIP_VERSION=$(pip3 --version 2>&1)
    success "pip3 установлен: $PIP_VERSION"
else
    error "pip3 не найден!"
    ((ERRORS++))
fi

# Проверка директории проекта
echo -n "Проверка директории проекта... "
if [ -d "/root/PyrusTelegramBot" ]; then
    cd /root/PyrusTelegramBot
    success "Директория проекта найдена"
else
    error "Директория /root/PyrusTelegramBot не найдена!"
    ((ERRORS++))
    exit 1
fi

echo ""
echo "📋 2. ПРОВЕРКА ФАЙЛОВ ПРОЕКТА"
echo "============================="

# Критически важные файлы
REQUIRED_FILES=(
    "app/__init__.py"
    "app/api.py"
    "app/bot.py"
    "app/worker.py"
    "app/db.py"
    "app/utils.py"
    "app/models.py"
    "requirements.txt"
    ".env"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "Файл $file найден"
    else
        error "Файл $file отсутствует!"
        ((ERRORS++))
    fi
done

echo ""
echo "📋 3. ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ"
echo "==================================="

if [ -f ".env" ]; then
    source .env
    
    # Критически важные переменные
    REQUIRED_VARS=(
        "BOT_TOKEN"
        "ADMIN_IDS"
        "SUPABASE_URL"
        "SUPABASE_KEY"
        "PYRUS_LOGIN"
        "PYRUS_SECURITY_KEY"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -n "${!var}" ]; then
            success "$var установлена (${#!var} символов)"
        else
            error "$var НЕ УСТАНОВЛЕНА!"
            ((ERRORS++))
        fi
    done
    
    # Проверка дополнительных переменных
    if [ -n "$PYRUS_WEBHOOK_SECRET" ]; then
        if [ "$PYRUS_WEBHOOK_SECRET" = "ЗАМЕНИ_НА_РЕАЛЬНЫЙ_СЕКРЕТ" ] || [ "$PYRUS_WEBHOOK_SECRET" = "temporary_placeholder" ]; then
            warning "PYRUS_WEBHOOK_SECRET использует заглушку (проверка подписи отключена)"
        else
            success "PYRUS_WEBHOOK_SECRET настроен"
        fi
    fi
    
    if [ "$DEV_SKIP_PYRUS_SIG" = "true" ]; then
        warning "DEV_SKIP_PYRUS_SIG=true (проверка подписи отключена)"
    fi
    
else
    error "Файл .env не найден!"
    ((ERRORS++))
fi

echo ""
echo "📋 4. ПРОВЕРКА ЗАВИСИМОСТЕЙ PYTHON"
echo "=================================="

echo -n "Установка/проверка зависимостей... "
if pip3 install -r requirements.txt >/dev/null 2>&1; then
    success "Все зависимости установлены"
else
    error "Ошибка установки зависимостей!"
    ((ERRORS++))
fi

# Проверка критически важных модулей
REQUIRED_MODULES=(
    "fastapi"
    "uvicorn"
    "telegram"
    "supabase"
    "pydantic"
    "dotenv"
)

for module in "${REQUIRED_MODULES[@]}"; do
    if python3 -c "import $module" 2>/dev/null; then
        success "Модуль $module доступен"
    else
        error "Модуль $module НЕ НАЙДЕН!"
        ((ERRORS++))
    fi
done

echo ""
echo "📋 5. ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЙ"
echo "=============================="

# Тест подключения к базе данных
echo -n "Тест подключения к Supabase... "
DB_TEST=$(python3 -c "
from dotenv import load_dotenv
load_dotenv()
try:
    from app.db import db
    settings = db.settings_get('service_enabled')
    print(f'SUCCESS:{settings}')
except Exception as e:
    print(f'ERROR:{e}')
" 2>&1)

if [[ $DB_TEST == SUCCESS:* ]]; then
    success "База данных подключена, service_enabled=${DB_TEST#SUCCESS:}"
else
    error "База данных: ${DB_TEST#ERROR:}"
    ((ERRORS++))
fi

# Тест Telegram API
echo -n "Тест подключения к Telegram... "
TG_TEST=$(python3 -c "
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

async def test_telegram():
    try:
        import telegram
        bot_token = os.getenv('BOT_TOKEN')
        if bot_token:
            bot = telegram.Bot(token=bot_token)
            me = await bot.get_me()
            print(f'SUCCESS:@{me.username}')
        else:
            print('ERROR:BOT_TOKEN не установлен')
    except Exception as e:
        print(f'ERROR:{e}')

asyncio.run(test_telegram())
" 2>&1)

if [[ $TG_TEST == SUCCESS:* ]]; then
    success "Telegram бот подключен: ${TG_TEST#SUCCESS:}"
else
    error "Telegram: ${TG_TEST#ERROR:}"
    ((ERRORS++))
fi

echo ""
echo "📋 6. ПРОВЕРКА SYSTEMD СЕРВИСОВ"
echo "==============================="

SERVICES=("pyrus-api" "pyrus-bot" "pyrus-worker")

for service in "${SERVICES[@]}"; do
    echo -n "Проверка сервиса $service... "
    
    if systemctl is-enabled $service >/dev/null 2>&1; then
        if systemctl is-active $service >/dev/null 2>&1; then
            success "$service активен и работает"
        else
            error "$service включен но НЕ РАБОТАЕТ!"
            ((ERRORS++))
            info "Статус: $(systemctl status $service --no-pager -l | head -3 | tail -1)"
        fi
    else
        error "$service НЕ НАСТРОЕН!"
        ((ERRORS++))
    fi
done

echo ""
echo "📋 7. ПРОВЕРКА ПОРТОВ И API"
echo "=========================="

# Проверка порта 8000
echo -n "Проверка API на порту 8000... "
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
    success "API отвечает: $HEALTH_RESPONSE"
else
    error "API не отвечает на порту 8000!"
    ((ERRORS++))
fi

# Тест webhook endpoint
echo -n "Тест webhook endpoint... "
WEBHOOK_TEST=$(curl -s -X POST http://localhost:8000/pyrus/webhook \
    -H "Content-Type: application/json" \
    -d '{"event":"test","task":{"id":1}}' 2>&1)

if [[ $WEBHOOK_TEST == *"webhook processed"* ]]; then
    success "Webhook endpoint работает"
else
    error "Webhook endpoint не работает: $WEBHOOK_TEST"
    ((ERRORS++))
fi

echo ""
echo "📋 8. ПРОВЕРКА ЛОГОВ"
echo "==================="

for service in "${SERVICES[@]}"; do
    echo "Последние логи $service:"
    echo "------------------------"
    journalctl -u $service --lines=3 --no-pager | tail -3
    echo ""
done

echo ""
echo "📋 9. ПРОВЕРКА РЕСУРСОВ"
echo "======================="

# Использование диска
echo "💾 Использование диска:"
df -h / | tail -1

# Использование памяти
echo "🧠 Использование памяти:"
free -h | head -2

# Процессы Python
echo "⚙️ Процессы Python:"
ps aux | grep python | grep -v grep | head -5

echo ""
echo "📋 10. ВНЕШНИЙ ДОСТУП"
echo "====================="

# Получаем внешний IP
EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || echo "не определен")
echo "🌐 Внешний IP: $EXTERNAL_IP"

# Тест внешнего доступа
echo -n "Тест внешнего доступа к API... "
if timeout 10 curl -s http://$EXTERNAL_IP:8000/health >/dev/null 2>&1; then
    success "API доступен извне"
else
    warning "API может быть недоступен извне (firewall?)"
    ((WARNINGS++))
fi

echo ""
echo "🎯 ИТОГОВЫЙ ОТЧЕТ"
echo "=================="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 ВСЕ ОТЛИЧНО! Система полностью готова к работе!${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}✅ Система работает с небольшими замечаниями${NC}"
    echo -e "${YELLOW}⚠️ Предупреждений: $WARNINGS${NC}"
else
    echo -e "${RED}❌ ЕСТЬ ПРОБЛЕМЫ, требующие исправления!${NC}"
    echo -e "${RED}💥 Ошибок: $ERRORS${NC}"
    echo -e "${YELLOW}⚠️ Предупреждений: $WARNINGS${NC}"
fi

echo ""
echo "📝 СЛЕДУЮЩИЕ ШАГИ:"
echo "=================="

if [ $ERRORS -gt 0 ]; then
    echo "🔧 Исправьте ошибки выше и перезапустите диагностику"
    echo "🔄 Перезапуск сервисов: systemctl restart pyrus-api pyrus-bot pyrus-worker"
else
    echo "✅ Настройте Pyrus webhook на: http://$EXTERNAL_IP:8000/pyrus/webhook"
    echo "🤖 Протестируйте бота в Telegram"
    echo "📊 Мониторинг: journalctl -u pyrus-* -f"
fi

echo ""
echo "🔍 Диагностика завершена: $(date)"
echo "=========================================="

exit $ERRORS
