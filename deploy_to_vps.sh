#!/bin/bash

# 🚀 Скрипт деплоя Pyrus Telegram Bot на VPS
# Использование: ./deploy_to_vps.sh

set -e  # Остановка при любой ошибке

VPS_HOST="195.133.81.197"
VPS_USER="root"
PROJECT_DIR="PyrusTelegramBot"
BACKUP_DIR="backups"

echo "🚀 ДЕПЛОЙ PYRUS TELEGRAM BOT"
echo "============================="
echo "VPS: $VPS_HOST"
echo "Пользователь: $VPS_USER"
echo ""

# Проверка доступности VPS
echo "🔗 Проверка доступности VPS..."
if ! ping -c 1 $VPS_HOST >/dev/null 2>&1; then
    echo "❌ VPS недоступен!"
    exit 1
fi
echo "✅ VPS доступен"

# Функция для выполнения команд на VPS
run_on_vps() {
    ssh -o ConnectTimeout=10 $VPS_USER@$VPS_HOST "$1"
}

# Функция для копирования файлов на VPS
copy_to_vps() {
    scp -r "$1" $VPS_USER@$VPS_HOST:"$2"
}

echo ""
echo "📋 Этап 1: Резервное копирование..."
run_on_vps "
    mkdir -p $BACKUP_DIR
    if [ -d $PROJECT_DIR ]; then
        BACKUP_NAME=backup_\$(date +%Y%m%d_%H%M%S).tar.gz
        echo \"📦 Создание резервной копии: \$BACKUP_NAME\"
        tar -czf $BACKUP_DIR/\$BACKUP_NAME $PROJECT_DIR/
        echo \"✅ Резервная копия создана\"
        ls -la $BACKUP_DIR/\$BACKUP_NAME
    else
        echo \"ℹ️ Старой версии проекта не найдено\"
    fi
"

echo ""
echo "📋 Этап 2: Остановка старых процессов..."
run_on_vps "
    echo \"🛑 Остановка старых процессов...\"
    pkill -f 'uvicorn.*pyrus' || echo \"API уже остановлен\"
    pkill -f 'python.*bot' || echo \"Bot уже остановлен\"
    pkill -f 'python.*worker' || echo \"Worker уже остановлен\"
    systemctl stop pyrus-api pyrus-bot pyrus-worker 2>/dev/null || echo \"Systemd сервисы не настроены\"
    sleep 2
    echo \"✅ Старые процессы остановлены\"
"

echo ""
echo "📋 Этап 3: Обновление кода..."
if run_on_vps "test -d $PROJECT_DIR/.git"; then
    echo "🔄 Обновление через git..."
    run_on_vps "
        cd $PROJECT_DIR
        git stash push -m 'Before deploy \$(date)'
        git pull origin main
        echo \"✅ Код обновлен через git\"
    "
else
    echo "📥 Первоначальная загрузка..."
    run_on_vps "rm -rf $PROJECT_DIR"
    
    # Копируем весь проект
    echo "📤 Копирование файлов на VPS..."
    copy_to_vps "." "$PROJECT_DIR"
    
    echo "✅ Код загружен на VPS"
fi

echo ""
echo "📋 Этап 4: Проверка и установка зависимостей..."
run_on_vps "
    cd $PROJECT_DIR
    echo \"🔍 Проверка Python и pip...\"
    python3 --version
    pip3 --version
    
    echo \"📦 Установка зависимостей...\"
    pip3 install -r requirements.txt
    echo \"✅ Зависимости установлены\"
"

echo ""
echo "📋 Этап 5: Проверка переменных окружения..."
run_on_vps "
    cd $PROJECT_DIR
    if [ ! -f .env ]; then
        echo \"⚠️ Файл .env не найден!\"
        echo \"📝 Создаем .env из примера...\"
        cp .env.example .env
        echo \"❗ ВНИМАНИЕ: Необходимо настроить .env файл с продакшн значениями!\"
        echo \"   Отредактируйте файл: nano .env\"
        echo \"   Особенно важно настроить:\"
        echo \"   - BOT_TOKEN\"
        echo \"   - ADMIN_IDS\"
        echo \"   - PYRUS_* переменные\"
        echo \"   - SUPABASE_* переменные\"
    else
        echo \"✅ Файл .env найден\"
    fi
    
    echo \"🔍 Проверка ключевых переменных...\"
    python3 -c \"
import os
from dotenv import load_dotenv
load_dotenv()

vars_to_check = ['BOT_TOKEN', 'ADMIN_IDS', 'SUPABASE_URL', 'PYRUS_LOGIN']
missing = []
for var in vars_to_check:
    if not os.getenv(var):
        missing.append(var)

if missing:
    print(f'❌ Отсутствуют переменные: {missing}')
    print('📝 Настройте их в .env файле перед продолжением')
    exit(1)
else:
    print('✅ Основные переменные настроены')
    \"
"

echo ""
echo "📋 Этап 6: Тестирование подключений..."
run_on_vps "
    cd $PROJECT_DIR
    echo \"🧪 Тестирование подключений...\"
    python3 -c \"
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

print('🔍 Проверка подключений...')

# Тест БД
try:
    from app.db import db
    settings = db.settings_get('service_enabled')
    print(f'✅ БД подключена, service_enabled: {settings}')
except Exception as e:
    print(f'❌ БД ошибка: {e}')
    exit(1)

# Тест Telegram
async def test_telegram():
    try:
        import telegram
        bot_token = os.getenv('BOT_TOKEN')
        if bot_token:
            bot = telegram.Bot(token=bot_token)
            me = await bot.get_me()
            print(f'✅ Telegram бот: @{me.username}')
        else:
            print('⚠️ BOT_TOKEN не установлен')
    except Exception as e:
        print(f'❌ Telegram ошибка: {e}')

asyncio.run(test_telegram())
print('✅ Проверки завершены')
    \"
"

echo ""
echo "📋 Этап 7: Настройка systemd сервисов..."
run_on_vps "
    cd $PROJECT_DIR
    
    echo \"🔧 Создание systemd сервисов...\"
    
    # API сервис
    cat > /etc/systemd/system/pyrus-api.service << 'EOF'
[Unit]
Description=Pyrus Telegram Bot API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/PyrusTelegramBot
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/python3 -m uvicorn app.api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Bot сервис
    cat > /etc/systemd/system/pyrus-bot.service << 'EOF'
[Unit]
Description=Pyrus Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/PyrusTelegramBot
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/python3 -m app.bot
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Worker сервис
    cat > /etc/systemd/system/pyrus-worker.service << 'EOF'
[Unit]
Description=Pyrus Notification Worker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/PyrusTelegramBot
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/python3 -m app.worker
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo \"✅ Systemd сервисы созданы\"
"

echo ""
echo "📋 Этап 8: Запуск сервисов..."
run_on_vps "
    echo \"🔄 Перезагрузка systemd...\"
    systemctl daemon-reload
    
    echo \"🔧 Включение автозапуска сервисов...\"
    systemctl enable pyrus-api pyrus-bot pyrus-worker
    
    echo \"🚀 Запуск сервисов...\"
    systemctl start pyrus-api
    sleep 3
    systemctl start pyrus-bot
    sleep 3
    systemctl start pyrus-worker
    
    echo \"✅ Сервисы запущены\"
"

echo ""
echo "📋 Этап 9: Проверка состояния..."
run_on_vps "
    echo \"📊 Статус сервисов:\"
    systemctl status pyrus-api --no-pager -l
    echo \"\"
    systemctl status pyrus-bot --no-pager -l
    echo \"\"
    systemctl status pyrus-worker --no-pager -l
"

echo ""
echo "📋 Этап 10: Финальные проверки..."
sleep 5

echo "🔍 Проверка API..."
if curl -s http://$VPS_HOST:8000/health | grep -q "ok"; then
    echo "✅ API работает корректно"
else
    echo "❌ API не отвечает"
fi

echo ""
echo "🎉 ДЕПЛОЙ ЗАВЕРШЕН!"
echo "=================="
echo ""
echo "📝 Следующие шаги:"
echo "1. Настройте Pyrus вебхук на: http://$VPS_HOST:8000/pyrus/webhook"
echo "2. Протестируйте Telegram бота"
echo "3. Проверьте админ-команды"
echo ""
echo "📊 Мониторинг:"
echo "sudo journalctl -u pyrus-api -f       # Логи API"
echo "sudo journalctl -u pyrus-bot -f       # Логи бота"
echo "sudo journalctl -u pyrus-worker -f    # Логи воркера"
echo ""
echo "🔧 Управление:"
echo "sudo systemctl restart pyrus-api pyrus-bot pyrus-worker"
echo "sudo systemctl stop pyrus-api pyrus-bot pyrus-worker"
echo ""
echo "✅ Система готова к продакшну!"
