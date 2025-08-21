#!/bin/bash

# 🚀 УПРАВЛЕНИЕ PYRUS TELEGRAM BOT СИСТЕМОЙ
# Использование: ./pyrus_control.sh [команда]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Функции для красивого вывода
success() { echo -e "${GREEN}✅ $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
header() { echo -e "${PURPLE}🚀 $1${NC}"; }

# Переход в директорию проекта
cd /root/PyrusTelegramBot 2>/dev/null || {
    error "Директория /root/PyrusTelegramBot не найдена!"
    exit 1
}

# Функция показа помощи
show_help() {
    header "PYRUS TELEGRAM BOT - СИСТЕМА УПРАВЛЕНИЯ"
    echo "========================================"
    echo ""
    echo "📋 ОСНОВНЫЕ КОМАНДЫ:"
    echo "  start          - Запустить все сервисы"
    echo "  stop           - Остановить все сервисы" 
    echo "  restart        - Перезапустить все сервисы"
    echo "  status         - Показать статус сервисов"
    echo ""
    echo "🔧 УПРАВЛЕНИЕ:"
    echo "  enable         - Включить уведомления (service_enabled=true)"
    echo "  disable        - Отключить уведомления (service_enabled=false)"
    echo "  test-mode      - Переключить в тестовый режим (быстрые интервалы)"
    echo "  prod-mode      - Переключить в продакшн режим (3 часа)"
    echo ""
    echo "📊 МОНИТОРИНГ:"
    echo "  logs           - Показать логи всех сервисов"
    echo "  logs-api       - Логи только API"
    echo "  logs-bot       - Логи только Telegram бота"
    echo "  logs-worker    - Логи только воркера"
    echo "  logs-webhooks  - Логи вебхуков (raw файлы)"
    echo "  queue          - Показать очередь уведомлений"
    echo "  users          - Показать зарегистрированных пользователей"
    echo ""
    echo "🧪 ТЕСТИРОВАНИЕ:"
    echo "  test-webhook   - Отправить тестовый webhook"
    echo "  test-api       - Проверить API"
    echo "  diagnose       - Полная диагностика системы"
    echo ""
    echo "🔄 ОБСЛУЖИВАНИЕ:"
    echo "  update         - Обновить код из git"
    echo "  backup         - Создать резервную копию"
    echo "  cleanup        - Очистить старые логи"
    echo ""
    echo "Пример: ./pyrus_control.sh start"
}

# Функция запуска сервисов
start_services() {
    header "ЗАПУСК СЕРВИСОВ"
    systemctl start pyrus-api pyrus-bot pyrus-worker
    sleep 2
    systemctl status pyrus-api pyrus-bot pyrus-worker --no-pager -l
    success "Все сервисы запущены"
}

# Функция остановки сервисов
stop_services() {
    header "ОСТАНОВКА СЕРВИСОВ"
    systemctl stop pyrus-api pyrus-bot pyrus-worker
    success "Все сервисы остановлены"
}

# Функция перезапуска сервисов
restart_services() {
    header "ПЕРЕЗАПУСК СЕРВИСОВ"
    
    info "Останавливаем сервисы..."
    systemctl stop pyrus-api pyrus-bot pyrus-worker
    sleep 2
    
    info "Запускаем сервисы..."
    systemctl start pyrus-api pyrus-bot pyrus-worker
    sleep 5
    
    info "Проверяем статус..."
    systemctl is-active pyrus-api pyrus-bot pyrus-worker
    
    success "Все сервисы перезапущены"
    warning "Для детального статуса используйте: ./pyrus_control.sh status"
}

# Функция показа статуса
show_status() {
    header "СТАТУС СИСТЕМЫ"
    echo ""
    info "Статус сервисов:"
    systemctl status pyrus-api pyrus-bot pyrus-worker --no-pager -l
    echo ""
    info "Использование ресурсов:"
    echo "💾 Диск: $(df -h / | tail -1 | awk '{print $5 " используется"}')"
    echo "🧠 Память: $(free -h | grep Mem | awk '{print $3 "/" $2 " используется"}')"
    echo ""
    info "API проверка:"
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        success "API работает (порт 8000)"
    else
        error "API не отвечает"
    fi
}

# Функция включения уведомлений
enable_notifications() {
    header "ВКЛЮЧЕНИЕ УВЕДОМЛЕНИЙ"
    python3 -c "
from dotenv import load_dotenv
load_dotenv()
from app.db import db
db.settings_set('service_enabled', 'true')
print('✅ Уведомления ВКЛЮЧЕНЫ')
"
    systemctl restart pyrus-worker
    success "Воркер перезапущен с новыми настройками"
}

# Функция отключения уведомлений
disable_notifications() {
    header "ОТКЛЮЧЕНИЕ УВЕДОМЛЕНИЙ"
    python3 -c "
from dotenv import load_dotenv
load_dotenv()
from app.db import db
db.settings_set('service_enabled', 'false')
print('⏸️ Уведомления ОТКЛЮЧЕНЫ')
"
    success "Очередь продолжает наполняться, но сообщения не отправляются"
}

# Функция переключения в тестовый режим
test_mode() {
    header "ПЕРЕКЛЮЧЕНИЕ В ТЕСТОВЫЙ РЕЖИМ"
    
    # Создаем backup текущего .env
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    
    # Устанавливаем тестовые значения
    sed -i 's/DELAY_HOURS=.*/DELAY_HOURS=0.02/' .env
    sed -i 's/REPEAT_INTERVAL_HOURS=.*/REPEAT_INTERVAL_HOURS=0.03/' .env
    sed -i 's/TTL_HOURS=.*/TTL_HOURS=0.1/' .env
    sed -i 's/QUIET_START=.*/QUIET_START=23:59/' .env
    sed -i 's/QUIET_END=.*/QUIET_END=23:58/' .env
    
    systemctl restart pyrus-worker
    success "Тестовый режим активирован"
    warning "Уведомления будут приходить через 1-2 минуты!"
    info "Для возврата в продакшн: ./pyrus_control.sh prod-mode"
}

# Функция переключения в продакшн режим
prod_mode() {
    header "ПЕРЕКЛЮЧЕНИЕ В ПРОДАКШН РЕЖИМ"
    
    # Устанавливаем продакшн значения
    sed -i 's/DELAY_HOURS=.*/DELAY_HOURS=3/' .env
    sed -i 's/REPEAT_INTERVAL_HOURS=.*/REPEAT_INTERVAL_HOURS=3/' .env
    sed -i 's/TTL_HOURS=.*/TTL_HOURS=24/' .env
    sed -i 's/QUIET_START=.*/QUIET_START=22:00/' .env
    sed -i 's/QUIET_END=.*/QUIET_END=09:00/' .env
    
    systemctl restart pyrus-worker
    success "Продакшн режим активирован"
    info "Уведомления будут приходить через 3 часа после упоминания"
}

# Функция показа логов
show_logs() {
    header "ЛОГИ ВСЕХ СЕРВИСОВ"
    journalctl -u pyrus-api -u pyrus-bot -u pyrus-worker -f --lines=20
}

show_logs_api() {
    header "ЛОГИ API"
    journalctl -u pyrus-api -f --lines=30
}

show_logs_bot() {
    header "ЛОГИ TELEGRAM БОТА"
    journalctl -u pyrus-bot -f --lines=30
}

show_logs_worker() {
    header "ЛОГИ ВОРКЕРА"
    journalctl -u pyrus-worker -f --lines=30
}

# Функция показа логов вебхуков
show_webhook_logs() {
    header "ЛОГИ PYRUS WEBHOOKS"
    if [ -d "logs" ]; then
        echo "📂 Найдены файлы логов:"
        ls -la logs/pyrus_raw_*.ndjson 2>/dev/null || echo "📭 Нет файлов логов"
        echo ""
        echo "🔍 Последние 10 записей:"
        tail -10 logs/pyrus_raw_*.ndjson 2>/dev/null | jq -r '.timestamp + " | " + .status + " | " + (.payload.event // "unknown")' 2>/dev/null || tail -10 logs/pyrus_raw_*.ndjson 2>/dev/null || echo "Нет логов для отображения"
    else
        echo "📂 Папка logs не найдена"
    fi
}

# Функция показа очереди
show_queue() {
    header "ОЧЕРЕДЬ УВЕДОМЛЕНИЙ"
    python3 -c "
from dotenv import load_dotenv
load_dotenv()
from app.db import db
from datetime import datetime
import pytz

# Проверяем настройки
service_enabled = db.settings_get('service_enabled')
print(f'📊 Сервис уведомлений: {service_enabled}')

# Показываем очередь
result = db.client.table('pending_notifications').select('*').execute()
print(f'📬 Записей в очереди: {len(result.data)}')

if result.data:
    print()
    print('📋 Детали очереди:')
    for i, record in enumerate(result.data, 1):
        next_send = record['next_send_at']
        print(f'{i}. Task {record[\"task_id\"]} → User {record[\"user_id\"]}')
        print(f'   Отправить: {next_send}')
        print(f'   Отправлено раз: {record[\"times_sent\"]}')
        print()
else:
    print('📭 Очередь пуста')
"
}

# Функция показа пользователей
show_users() {
    header "ЗАРЕГИСТРИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ"
    python3 -c "
from dotenv import load_dotenv
load_dotenv()
from app.db import db

users = db.get_all_users()
print(f'👥 Всего пользователей: {len(users)}')

if users:
    print()
    for i, user in enumerate(users, 1):
        print(f'{i}. {user.full_name or f\"User {user.user_id}\"}')
        print(f'   Pyrus ID: {user.user_id}')
        print(f'   Telegram: {user.telegram_id}')
        print(f'   Телефон: {user.phone or \"не указан\"}')
        print()
else:
    print('📭 Нет зарегистрированных пользователей')
    print('💡 Найдите бота в Telegram и отправьте /start')
"
}

# Функция тестового webhook
test_webhook() {
    header "ТЕСТ WEBHOOK"
    
    USER_ID=164266775  # Ваш ID
    
    curl -X POST http://localhost:8000/pyrus/webhook \
        -H "Content-Type: application/json" \
        -d '{
            "event": "comment",
            "task": {
                "id": 99999,
                "subject": "ТЕСТОВАЯ задача",
                "comments": [{
                    "id": 888888,
                    "text": "Тест уведомления от скрипта!",
                    "create_date": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
                    "author": {"id": 777, "first_name": "Test", "last_name": "Script"},
                    "mentions": ['$USER_ID']
                }]
            },
            "actor": {"id": 777, "first_name": "Test", "last_name": "Script"}
        }'
    
    echo ""
    success "Тестовый webhook отправлен"
    info "Проверьте логи воркера: ./pyrus_control.sh logs-worker"
}

# Функция теста API
test_api() {
    header "ТЕСТ API"
    
    echo -n "Проверка health endpoint... "
    if curl -s http://localhost:8000/health | grep -q "ok"; then
        success "API работает"
    else
        error "API не отвечает"
    fi
    
    echo -n "Проверка webhook endpoint... "
    RESPONSE=$(curl -s -X POST http://localhost:8000/pyrus/webhook \
        -H "Content-Type: application/json" \
        -d '{"event":"test","task":{"id":1}}')
    
    if echo "$RESPONSE" | grep -q "webhook processed"; then
        success "Webhook endpoint работает"
    else
        error "Webhook endpoint не работает"
    fi
}

# Функция обновления кода
update_code() {
    header "ОБНОВЛЕНИЕ КОДА"
    
    git stash push -m "Auto stash before update $(date)"
    git pull origin main
    pip3 install -r requirements.txt
    
    success "Код обновлен"
    warning "Рекомендуется перезапустить сервисы: ./pyrus_control.sh restart"
}

# Функция создания backup
create_backup() {
    header "СОЗДАНИЕ РЕЗЕРВНОЙ КОПИИ"
    
    BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf ~/backups/$BACKUP_NAME . --exclude='.git' --exclude='logs' --exclude='__pycache__'
    
    success "Backup создан: ~/backups/$BACKUP_NAME"
}

# Функция очистки
cleanup() {
    header "ОЧИСТКА СИСТЕМЫ"
    
    # Очистка логов старше 7 дней
    find logs/ -name "*.ndjson" -mtime +7 -delete 2>/dev/null || true
    
    # Очистка Python кэша
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    success "Очистка завершена"
}

# Главная логика
case "${1:-help}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    enable)
        enable_notifications
        ;;
    disable)
        disable_notifications
        ;;
    test-mode)
        test_mode
        ;;
    prod-mode)
        prod_mode
        ;;
    logs)
        show_logs
        ;;
    logs-api)
        show_logs_api
        ;;
    logs-bot)
        show_logs_bot
        ;;
    logs-worker)
        show_logs_worker
        ;;
    logs-webhooks)
        show_webhook_logs
        ;;
    queue)
        show_queue
        ;;
    users)
        show_users
        ;;
    test-webhook)
        test_webhook
        ;;
    test-api)
        test_api
        ;;
    diagnose)
        ./diagnose_system.sh
        ;;
    update)
        update_code
        ;;
    backup)
        create_backup
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Неизвестная команда: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
