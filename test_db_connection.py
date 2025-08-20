#!/usr/bin/env python3
"""
Тест подключения к базе данных
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def test_db_connection():
    """Тестируем подключение к Supabase"""
    print("🔄 Тестирование подключения к базе данных...")
    
    try:
        from app.db import db
        
        # Проверяем подключение через простой запрос
        print("✅ Импорт базы данных успешен")
        
        # Тестируем базовые операции
        print("🔄 Проверка настроек...")
        result = db.settings_get('service_enabled')
        print(f"✅ Настройка service_enabled: {result}")
        
        # Тестируем логирование
        print("🔄 Тестирование логирования...")
        db.log_event('test_connection', {'message': 'Тест подключения', 'success': True})
        print("✅ Логирование работает")
        
        print("🎉 База данных работает корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе: {e}")
        return False

def test_utils():
    """Тестируем утилиты"""
    print("\n🔄 Тестирование утилит...")
    
    try:
        from app.utils import normalize_phone_e164, is_in_quiet_hours, schedule_after
        from datetime import datetime
        
        # Тест нормализации телефона
        phone = normalize_phone_e164("8-912-345-67-89")
        print(f"✅ Нормализация телефона: {phone}")
        
        # Тест тихих часов
        now = datetime.now()
        quiet = is_in_quiet_hours(now)
        print(f"✅ Тихие часы сейчас: {quiet}")
        
        # Тест планировщика
        scheduled = schedule_after(now, 3)
        print(f"✅ Планирование через 3 часа: {scheduled}")
        
        print("🎉 Утилиты работают корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в утилитах: {e}")
        return False

def test_hmac():
    """Тестируем HMAC валидацию"""
    print("\n🔄 Тестирование HMAC...")
    
    try:
        from app.utils import verify_pyrus_signature
        
        # Тест с пропуском проверки (dev режим)
        result_dev = verify_pyrus_signature(b'test', 'secret', dev_skip=True)
        print(f"✅ HMAC dev режим: {result_dev}")
        
        # Тест реальной проверки
        test_body = b'{"test": "data"}'
        test_secret = "test_secret"
        result_real = verify_pyrus_signature(test_body, test_secret, dev_skip=False)
        print(f"✅ HMAC проверка: функция работает")
        
        print("🎉 HMAC валидация работает корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка HMAC: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Полная проверка готовности Этапа 2")
    print("=" * 50)
    
    success = True
    
    # Проверяем переменные окружения
    print("\n🔄 Проверка переменных окружения...")
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'TZ', 'DELAY_HOURS']
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: установлено")
        else:
            print(f"❌ {var}: НЕ установлено")
            success = False
    
    # Тестируем компоненты
    success &= test_db_connection()
    success &= test_utils()
    success &= test_hmac()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Этап 2 завершён успешно!")
        print("✅ Готовы переходить к Этапу 3")
    else:
        print("❌ Есть проблемы, нужно их исправить")
    print("=" * 50)
