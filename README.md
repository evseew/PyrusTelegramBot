# Pyrus Telegram Bot

Умный бот для уведомлений из Pyrus с задержкой 3 часа и обработкой реакций.

## Быстрый старт

1. Установка зависимостей:
```bash
pip install -r requirements.txt
```

2. Настройка переменных окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими данными
```

3. Запуск API (этап 1 - заглушка):
```bash
uvicorn app.api:app --host 0.0.0.0 --port 80
```

Или для разработки на порту 8000:
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

## Проверка работы

- Здоровье сервиса: `curl http://localhost:8000/health`
- Логи вебхуков сохраняются в папке `logs/`

## Этапы разработки

- ✅ Этап 1: Базовая заглушка для приёма вебхуков
- ✅ Этап 2: База данных и утилиты  
- ✅ Этап 3: Обработка Pyrus вебхуков
- ✅ Этап 4: Фоновый воркер
- ✅ Этап 5: Telegram бот
- ⏳ Этап 6: Production deployment

## Запуск системы

### Быстрый старт (все компоненты):
```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp env.example .env
# Отредактируйте .env с вашими данными

# Запуск всех компонентов
python run_stage5.py --component all
```

### Отдельные компоненты:
```bash
# Только API
python run_stage5.py --component api

# Только Telegram бот
python run_stage5.py --component bot

# Только воркер
python run_stage5.py --component worker
```

## Тестирование

```bash
# Полная интеграционная проверка
python test_stage5_integration.py

# Проверка здоровья API
curl http://localhost:8000/health
```

## Структура проекта

```
PyrusTelegramBot/
├── app/
│   ├── api.py          # FastAPI сервер (вебхуки)
│   ├── bot.py          # Telegram бот (команды)
│   ├── worker.py       # Фоновый воркер (уведомления)
│   ├── db.py          # База данных Supabase
│   ├── utils.py       # Утилиты (HMAC, планировщик)
│   └── models.py      # Модели данных Pydantic
├── logs/              # Логи вебхуков (создаётся автоматически)
├── requirements.txt   # Зависимости Python
├── .env.example      # Пример настроек
├── run_stage5.py     # Скрипт запуска
├── test_stage5_integration.py  # E2E тесты
├── STAGE5_COMPLETED.md # Документация Этапа 5
└── README.md         # Общая документация
``` 