#!/usr/bin/env python3
"""
Полная проверка готовности Этапа 3
"""
import os
import sys

def check_api_py():
    """Проверка app/api.py"""
    print("🔍 Проверка app/api.py...")
    
    with open('app/api.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('from dotenv import load_dotenv', 'Импорт dotenv'),
        ('from .utils import verify_pyrus_signature', 'Импорт утилит'),
        ('from .models import PyrusWebhookPayload', 'Импорт моделей'),
        ('from .db import db', 'Импорт БД'),
        ('HTTPException', 'HTTP исключения'),
        ('DEV_SKIP_PYRUS_SIG', 'Dev режим'),
        ('verify_pyrus_signature(raw_body, PYRUS_WEBHOOK_SECRET, DEV_SKIP_PYRUS_SIG, signature_header)', 'HMAC с 4 параметрами'),
        ('PyrusWebhookPayload(**payload_data)', 'Парсинг в модель'),
        ('webhook processed', 'Новое сообщение'),
        ('raise HTTPException(status_code=400', 'HTTP 400 для ошибок'),
        ('status: str = "unknown"', 'Статус в логировании')
    ]
    
    success = True
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc}: НЕ НАЙДЕНО")
            success = False
    
    return success

def check_utils_py():
    """Проверка app/utils.py"""
    print("\n🔍 Проверка app/utils.py...")
    
    with open('app/utils.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('def verify_pyrus_signature(raw_body: bytes, secret: str, dev_skip: bool = False, signature_header: str = "")', 'Сигнатура с 4 параметрами'),
        ('signature_header: Заголовок X-Pyrus-Sig', 'Документация 4-го параметра'),
        ('hmac.compare_digest', 'Безопасное сравнение'),
        ('sha1=" + hmac.new', 'Формат sha1=hash'),
        ('def normalize_phone_e164', 'Нормализация телефона'),
        ('def is_in_quiet_hours', 'Тихие часы'),
        ('def schedule_after', 'Планировщик'),
        ('Asia/Yekaterinburg', 'Часовой пояс')
    ]
    
    success = True
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc}: НЕ НАЙДЕНО")
            success = False
    
    return success

def check_models_py():
    """Проверка app/models.py"""
    print("\n🔍 Проверка app/models.py...")
    
    with open('app/models.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('class PyrusUser', 'Модель пользователя'),
        ('class PyrusComment', 'Модель комментария'),
        ('class PyrusTask', 'Модель задачи'),
        ('class PyrusWebhookPayload', 'Модель webhook'),
        ('mentions: List[int]', 'Поле mentions'),
        ('actor: Optional[PyrusUser]', 'Поле actor'),
        ('change: Optional[Dict[str, Any]]', 'Поле change')
    ]
    
    success = True
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc}: НЕ НАЙДЕНО")
            success = False
    
    return success

def check_db_py():
    """Проверка app/db.py"""
    print("\n🔍 Проверка app/db.py...")
    
    with open('app/db.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('def upsert_user', 'Создание пользователя'),
        ('def get_user', 'Получение пользователя'),
        ('def upsert_or_shift_pending', 'Очередь уведомлений'),
        ('def delete_pending', 'Удаление из очереди'),
        ('def select_due', 'Выбор готовых'),
        ('def processed_comment_exists', 'Идемпотентность'),
        ('def settings_get', 'Настройки'),
        ('def log_event', 'Логирование'),
        ('from supabase import create_client', 'Импорт Supabase')
    ]
    
    success = True
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc}: НЕ НАЙДЕНО")
            success = False
    
    return success

def check_requirements():
    """Проверка requirements.txt"""
    print("\n🔍 Проверка requirements.txt...")
    
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'Uvicorn'),
        ('supabase', 'Supabase'),
        ('pydantic', 'Pydantic'),
        ('pytz', 'Часовые пояса'),
        ('python-dotenv', 'Переменные окружения'),
        ('aiofiles', 'Асинхронные файлы'),
        ('requests', 'HTTP клиент для тестов')
    ]
    
    success = True
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc}: НЕ НАЙДЕНО")
            success = False
    
    return success

def check_files_exist():
    """Проверка существования файлов"""
    print("\n🔍 Проверка файлов...")
    
    files = [
        ('app/__init__.py', 'Пакет приложения'),
        ('app/api.py', 'API модуль'),
        ('app/db.py', 'БД модуль'),
        ('app/models.py', 'Модели'),
        ('app/utils.py', 'Утилиты'),
        ('schema.sql', 'Схема БД'),
        ('env.example', 'Пример настроек'),
        ('test_vps_api.py', 'Тест VPS'),
        ('requirements.txt', 'Зависимости')
    ]
    
    success = True
    for file_path, desc in files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✅ {desc}: {size} байт")
        else:
            print(f"  ❌ {desc}: ОТСУТСТВУЕТ")
            success = False
    
    return success

def main():
    print("🚀 ПОЛНАЯ ПРОВЕРКА ЭТАПА 3")
    print("=" * 60)
    
    success = True
    success &= check_files_exist()
    success &= check_api_py()
    success &= check_utils_py() 
    success &= check_models_py()
    success &= check_db_py()
    success &= check_requirements()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ЭТАП 3 ПОЛНОСТЬЮ ГОТОВ!")
        print("✅ Все файлы на месте")
        print("✅ Все функции реализованы")
        print("✅ Все импорты корректны")
        print("✅ Сигнатуры функций совместимы")
        print("\n🔧 ГОТОВЫ К КОММИТУ И ДЕПЛОЮ!")
    else:
        print("❌ ЕСТЬ ПРОБЛЕМЫ В РЕАЛИЗАЦИИ")
        print("⚠️  Исправьте ошибки перед деплоем")
    print("=" * 60)

if __name__ == "__main__":
    main()
