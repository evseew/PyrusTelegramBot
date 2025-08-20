# Обновление кода Этапа 3 на VPS

## Текущая ситуация
✅ API работает на VPS (порт 8000)  
❌ Запущена старая версия (Этап 1) - возвращает `"webhook received"`  
🎯 Нужно обновить до новой версии (Этап 3) - должна возвращать `"webhook processed"`  

## Команды для VPS

### 1. Остановить текущий API
```bash
# В терминале где запущен uvicorn нажать Ctrl+C
# Или найти и убить процесс:
sudo kill $(ps aux | grep 'uvicorn.*8000' | grep -v grep | awk '{print $2}')
```

### 2. Обновить код
```bash
cd ~/PyrusTelegramBot

# Вариант A: Если используется git
git pull origin main

# Вариант B: Если код копируется вручную
# Скопировать обновленные файлы:
# - app/api.py (основные изменения)
# - app/db.py  
# - app/models.py
# - app/utils.py
# - requirements.txt
```

### 3. Обновить зависимости
```bash
pip3 install -r requirements.txt
```

### 4. Проверить .env файл
```bash
# Убедиться что есть переменная для dev режима:
echo "DEV_SKIP_PYRUS_SIG=true" >> .env
```

### 5. Запустить обновленный API
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

## Ожидаемые изменения

### До обновления (Этап 1):
```json
{"status": "ok", "message": "webhook received"}
```

### После обновления (Этап 3):
```json
{"status": "ok", "message": "webhook processed"}
```

## Проверка обновления

### Быстрая проверка
```bash
# Локально
curl -s -X POST http://195.133.81.197:8000/pyrus/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"test","task":{"id":1}}'

# Должно вернуть: "webhook processed"
```

### Полный тест
```bash
# Локально
python3 test_vps_api.py
```

## Ожидаемые результаты после обновления

✅ Health endpoint: `ok`  
✅ Валидный webhook: `"webhook processed"`  
✅ Невалидный JSON: HTTP 400  
✅ Логирование в БД Supabase  
✅ Обработка упоминаний и реакций  

## Возможные проблемы

### Ошибка импорта модулей
```bash
# Проверить что app/__init__.py существует
touch app/__init__.py
```

### Ошибка подключения к БД
```bash
# Проверить .env переменные
cat .env | grep SUPABASE
```

### Ошибка зависимостей
```bash
# Переустановить supabase с правильной версией
pip3 install supabase==1.0.3 websockets==11.0.3
```

---

**После успешного обновления и тестирования - Этап 3 завершён! 🚀**
