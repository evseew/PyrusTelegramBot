# 🚀 КОМАНДЫ ДЛЯ ВЫПОЛНЕНИЯ НА СЕРВЕРЕ

Подключитесь к серверу: `ssh root@195.133.81.197`

## 1. Остановка старых процессов
```bash
pkill -f uvicorn || echo "uvicorn не запущен"
pkill -f "python.*bot" || echo "bot не запущен"
pkill -f "python.*worker" || echo "worker не запущен"
systemctl stop pyrus-* 2>/dev/null || echo "systemd сервисы не настроены"
```

## 2. Обновление кода
```bash
cd ~
if [ -d "PyrusTelegramBot" ]; then
    cd PyrusTelegramBot
    git pull origin main
    echo "✅ Код обновлен"
else
    git clone https://github.com/YOUR_USERNAME/PyrusTelegramBot.git
    cd PyrusTelegramBot
    echo "✅ Код загружен"
fi
```

## 3. Создание .env файла
```bash
# Создаем .env из примера
cp .env.example .env

# Редактируем .env (вставьте ваши реальные значения)
nano .env
```

### Содержимое .env файла:
```env
# === КРИТИЧЕСКИ ВАЖНЫЕ ===
BOT_TOKEN=ваш_токен_от_botfather
ADMIN_IDS=164266775
SUPABASE_URL=ваш_supabase_url
SUPABASE_KEY=ваш_supabase_key
PYRUS_LOGIN=ваш_pyrus_login
PYRUS_SECURITY_KEY=ваш_pyrus_security_key

# === ВРЕМЕННО БЕЗ ПРОВЕРКИ ===
DEV_SKIP_PYRUS_SIG=true
PYRUS_WEBHOOK_SECRET=temporary_placeholder

# === НАСТРОЙКИ (можно оставить как есть) ===
DELAY_HOURS=3
REPEAT_INTERVAL_HOURS=3
TTL_HOURS=24
TZ=Asia/Yekaterinburg
QUIET_START=22:00
QUIET_END=09:00
TRUNC_TASK_TITLE_LEN=50
TRUNC_COMMENT_LEN=50
QUEUE_TOP_N=10
```

## 4. Установка зависимостей
```bash
pip3 install -r requirements.txt
```

## 5. Тест подключений
```bash
python3 -c "
from dotenv import load_dotenv
load_dotenv()
import asyncio
import os

# Тест БД
try:
    from app.db import db
    settings = db.settings_get('service_enabled')
    print(f'✅ БД: service_enabled={settings}')
except Exception as e:
    print(f'❌ БД: {e}')

# Тест Telegram
async def test_tg():
    try:
        import telegram
        bot = telegram.Bot(token=os.getenv('BOT_TOKEN'))
        me = await bot.get_me()
        print(f'✅ Telegram: @{me.username}')
    except Exception as e:
        print(f'❌ Telegram: {e}')

asyncio.run(test_tg())
"
```

## 6. Создание systemd сервисов
```bash
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

[Install]
WantedBy=multi-user.target
EOF
```

## 7. Запуск сервисов
```bash
# Перезагрузить systemd
systemctl daemon-reload

# Включить автозапуск
systemctl enable pyrus-api pyrus-bot pyrus-worker

# Запустить сервисы
systemctl start pyrus-api
sleep 3
systemctl start pyrus-bot
sleep 3
systemctl start pyrus-worker

# Проверить статус
systemctl status pyrus-api pyrus-bot pyrus-worker
```

## 8. Проверка работы
```bash
# Проверка API
curl http://localhost:8000/health

# Проверка логов
journalctl -u pyrus-api -f --lines=10 &
journalctl -u pyrus-bot -f --lines=10 &
journalctl -u pyrus-worker -f --lines=10 &

# Остановить просмотр логов: Ctrl+C
```

## 9. Внешний тест
```bash
# С локального компьютера
curl http://195.133.81.197:8000/health

# Тест webhook
curl -X POST http://195.133.81.197:8000/pyrus/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"test","task":{"id":1}}'
```

## 🔧 Управление сервисами
```bash
# Перезапуск всех
systemctl restart pyrus-api pyrus-bot pyrus-worker

# Остановка всех
systemctl stop pyrus-api pyrus-bot pyrus-worker

# Просмотр логов
journalctl -u pyrus-api -f
journalctl -u pyrus-bot -f
journalctl -u pyrus-worker -f
```

---

## 🎯 После успешного запуска:
1. Настройте вебхук в Pyrus на: `http://195.133.81.197:8000/pyrus/webhook`
2. Протестируйте бота в Telegram: найдите @PyrusTelegramBot
3. Отправьте `/start` и зарегистрируйтесь
4. Проверьте админ-команды: `/enable_all`, `/users`

**🎉 ГОТОВО!**
