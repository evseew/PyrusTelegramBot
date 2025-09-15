# 🚀 ПРОДАКШН ДЕПЛОЙ ЭТАПА 5

## Подготовка к деплою

### 📋 Чек-лист перед деплоем

**Локальные проверки:**
- [ ] Все тесты пройдены локально (`python3 test_stage5_integration.py`)
- [ ] Код зафиксирован в git
- [ ] .env файл с продакшн настройками готов
- [ ] BOT_TOKEN получен от @BotFather

**VPS проверки:**
- [ ] VPS доступен по SSH
- [ ] Резервная копия текущей версии создана
- [ ] Свободное место на диске достаточно
- [ ] Pyrus вебхук настроен на корректный URL

**Переменные окружения для продакшна:**
```bash
# Обязательные для полной функциональности
BOT_TOKEN=              # От @BotFather
ADMIN_IDS=              # Ваш Telegram chat_id
PYRUS_LOGIN=            # Логин администратора Pyrus
PYRUS_SECURITY_KEY=     # Ключ безопасности Pyrus  
PYRUS_WEBHOOK_SECRET=   # Секрет вебхука
SUPABASE_URL=           # URL вашей Supabase
SUPABASE_KEY=           # Anon key Supabase

# Настройки тайминга (можно оставить по умолчанию)
DELAY_HOURS=3
REPEAT_INTERVAL_HOURS=3
TTL_HOURS=24
TZ=Asia/Yekaterinburg
QUIET_START=22:00
QUIET_END=09:00
```

## Команды для деплоя

### 1. Подключение к VPS
```bash
ssh root@195.133.81.197
```

### 2. Резервное копирование
```bash
# На VPS
cd ~
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz PyrusTelegramBot/ || echo "Старой версии нет"
ls -la backup_*.tar.gz
```

### 3. Обновление кода
```bash
# Если git репозиторий существует
cd ~/PyrusTelegramBot
git pull origin main

# Или клонирование заново
cd ~
rm -rf PyrusTelegramBot
git clone <your-repo-url> PyrusTelegramBot
cd PyrusTelegramBot
```

### 4. Установка зависимостей
```bash
cd ~/PyrusTelegramBot
pip3 install -r requirements.txt
```

### 5. Настройка переменных окружения
```bash
cd ~/PyrusTelegramBot
cp .env.example .env
nano .env  # Вставить продакшн настройки
```

### 6. Проверка подключений
```bash
# Тест подключения к БД и Telegram
python3 -c "
from dotenv import load_dotenv
load_dotenv()

# Тест БД
try:
    from app.db import db
    settings = db.settings_get('service_enabled')
    print(f'✅ БД подключена, service_enabled: {settings}')
except Exception as e:
    print(f'❌ БД ошибка: {e}')

# Тест Telegram
import asyncio
import os
async def test_tg():
    try:
        import telegram
        bot = telegram.Bot(token=os.getenv('BOT_TOKEN'))
        me = await bot.get_me()
        print(f'✅ Telegram бот: @{me.username}')
    except Exception as e:
        print(f'❌ Telegram ошибка: {e}')

asyncio.run(test_tg())
"
```

### 7. Создание systemd сервисов

**API сервис:**
```bash
sudo tee /etc/systemd/system/pyrus-api.service > /dev/null <<EOF
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
```

**Telegram бот сервис:**
```bash
sudo tee /etc/systemd/system/pyrus-bot.service > /dev/null <<EOF
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
```

**Воркер сервис:**
```bash
sudo tee /etc/systemd/system/pyrus-worker.service > /dev/null <<EOF
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

### 8. Запуск сервисов
```bash
# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable pyrus-api pyrus-bot pyrus-worker

# Запустить сервисы
sudo systemctl start pyrus-api
sudo systemctl start pyrus-bot  
sudo systemctl start pyrus-worker

# Проверить статус
sudo systemctl status pyrus-api pyrus-bot pyrus-worker
```

### 9. Проверка работы
```bash
# API здоровье
curl http://localhost:8000/health

# Логи сервисов
sudo journalctl -u pyrus-api -f --lines=20
sudo journalctl -u pyrus-bot -f --lines=20  
sudo journalctl -u pyrus-worker -f --lines=20

# Тест webhook
curl -X POST http://195.133.81.197:8000/pyrus/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"test","task":{"id":1}}'
```

### 10. Настройка Pyrus вебхука
В админке Pyrus направить вебхук на:
```
http://195.133.81.197:8000/pyrus/webhook
```

### 11. Тестирование в Telegram
1. Найти бота @PyrusTelegramBot
2. Отправить `/start`
3. Отправить контакт для регистрации
4. Проверить админ-команды (если вы в ADMIN_IDS)

## Мониторинг

### Просмотр логов
```bash
# Логи всех сервисов
sudo journalctl -u pyrus-* -f

# Логи API
sudo journalctl -u pyrus-api -f

# Логи воркера
sudo journalctl -u pyrus-worker -f

# Файловые логи webhook
tail -f ~/PyrusTelegramBot/logs/pyrus_raw_*.ndjson
```

### Управление сервисами
```bash
# Перезапуск всех сервисов
sudo systemctl restart pyrus-api pyrus-bot pyrus-worker

# Остановка
sudo systemctl stop pyrus-api pyrus-bot pyrus-worker

# Статус
sudo systemctl status pyrus-api pyrus-bot pyrus-worker
```

### Обновление кода
```bash
cd ~/PyrusTelegramBot
git pull origin main
pip3 install -r requirements.txt
sudo systemctl restart pyrus-api pyrus-bot pyrus-worker
```

## Откат в случае проблем

### Быстрый откат
```bash
# Остановить новые сервисы
sudo systemctl stop pyrus-api pyrus-bot pyrus-worker

# Восстановить из резервной копии
cd ~
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz

# Запустить только API из старой версии
cd ~/PyrusTelegramBot
nohup python3 -m uvicorn app.api:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
```

---

**🎯 Цель:** Полнофункциональная система с автозапуском, мониторингом и отказоустойчивостью.
