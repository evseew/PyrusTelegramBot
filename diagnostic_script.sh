#!/bin/bash

echo "=== ДИАГНОСТИКА СИСТЕМЫ ==="
echo "Дата: $(date)"
echo "Машина: $(hostname)"
echo "OS: $(uname -a)"
echo ""

echo "=== PYTHON И ВИРТУАЛЬНОЕ ОКРУЖЕНИЕ ==="
echo "Python system version:"
python3 --version
echo ""

echo "Virtual environment python:"
cd /Users/test/Documents/CODE/PyrusTelegramBot
source venv/bin/activate
python --version
echo ""

echo "Pip freeze (все пакеты в venv):"
pip freeze
echo ""

echo "=== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==="
echo "Checking environment variables (без показа секретов):"
env | grep -E "(PYRUS|TELEGRAM|DATABASE|SUPABASE)" | sed 's/=.*/=***/' || echo "Нет переменных с PYRUS/TELEGRAM/DATABASE/SUPABASE"
echo ""

echo "=== ФАЙЛЫ КОНФИГУРАЦИИ ==="
echo "Проверка .env файла:"
if [ -f ".env" ]; then
    echo ".env существует, размер: $(wc -l < .env) строк"
    echo "Ключи в .env (без значений):"
    grep -v '^#' .env | grep '=' | cut -d'=' -f1 | sort
else
    echo ".env файл НЕ НАЙДЕН"
fi
echo ""

echo "Проверка env.example:"
if [ -f "env.example" ]; then
    echo "env.example существует:"
    cat env.example
else
    echo "env.example НЕ НАЙДЕН"
fi
echo ""

echo "=== БАЗА ДАННЫХ ==="
echo "Проверка schema.sql:"
if [ -f "schema.sql" ]; then
    echo "schema.sql существует, размер: $(wc -l < schema.sql) строк"
    echo "Первые 10 строк:"
    head -10 schema.sql
else
    echo "schema.sql НЕ НАЙДЕН"
fi
echo ""

echo "=== ЛОГИ И ОШИБКИ ==="
echo "Содержимое logs/ директории:"
ls -la logs/ 2>/dev/null || echo "Директория logs/ не найдена"
echo ""

echo "Последние записи в логах:"
if [ -d "logs" ]; then
    find logs/ -name "*.log" -o -name "*.ndjson" | head -3 | while read logfile; do
        echo "=== $logfile ==="
        tail -10 "$logfile" 2>/dev/null || echo "Не удалось прочитать $logfile"
        echo ""
    done
fi

echo "=== СЕТЕВЫЕ ПРОВЕРКИ ==="
echo "Проверка доступности Telegram API:"
curl -s --connect-timeout 5 https://api.telegram.org/bot123:test/getMe > /dev/null && echo "Telegram API доступен" || echo "Telegram API НЕДОСТУПЕН"

echo "Проверка доступности Pyrus API:"
curl -s --connect-timeout 5 https://pyrus.com/api/v4/auth > /dev/null && echo "Pyrus API доступен" || echo "Pyrus API НЕДОСТУПЕН"
echo ""

echo "=== ПОПЫТКА ЗАПУСКА ==="
echo "Пробуем запустить проверку импортов:"
python -c "
try:
    import app.bot
    print('✓ app.bot импортируется успешно')
except Exception as e:
    print(f'✗ Ошибка импорта app.bot: {e}')

try:
    import app.api
    print('✓ app.api импортируется успешно')
except Exception as e:
    print(f'✗ Ошибка импорта app.api: {e}')

try:
    import app.pyrus_client
    print('✓ app.pyrus_client импортируется успешно')
except Exception as e:
    print(f'✗ Ошибка импорта app.pyrus_client: {e}')

try:
    from app.db import get_db_connection
    conn = get_db_connection()
    print('✓ Подключение к БД успешно')
    conn.close()
except Exception as e:
    print(f'✗ Ошибка подключения к БД: {e}')
"

echo ""
echo "=== ПРАВА ДОСТУПА ==="
echo "Права на ключевые файлы:"
ls -la app/ | head -10
echo ""
ls -la .env* 2>/dev/null || echo "Нет .env файлов"
echo ""

deactivate 2>/dev/null || true
echo "=== ДИАГНОСТИКА ЗАВЕРШЕНА ==="


