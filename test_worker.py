#!/usr/bin/env python3
"""
Тест фонового воркера Этапа 4
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
sys.path.append('.')

from dotenv import load_dotenv
load_dotenv()

async def test_worker_import():
    """Тест импорта воркера"""
    print("🔄 Тестирование импорта воркера...")
    
    try:
        from app.worker import NotificationWorker, run_worker
        print("✅ Воркер импортирован успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

async def test_worker_configuration():
    """Тест конфигурации воркера"""
    print("\n🔄 Тестирование конфигурации...")
    
    try:
        from app.worker import (
            REPEAT_INTERVAL_HOURS, TTL_HOURS, TZ, 
            QUIET_START, QUIET_END, DRY_RUN
        )
        
        print(f"✅ Интервал повторов: {REPEAT_INTERVAL_HOURS}ч")
        print(f"✅ TTL: {TTL_HOURS}ч") 
        print(f"✅ Часовой пояс: {TZ}")
        print(f"✅ Тихие часы: {QUIET_START}-{QUIET_END}")
        print(f"✅ Режим DRY_RUN: {DRY_RUN}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

async def test_worker_methods():
    """Тест методов воркера"""
    print("\n🔄 Тестирование методов воркера...")
    
    try:
        from app.worker import NotificationWorker
        
        worker = NotificationWorker()
        print("✅ Создание экземпляра воркера")
        
        # Тест проверки настроек
        enabled = worker._is_service_enabled()
        print(f"✅ Проверка service_enabled: {enabled}")
        
        # Тест получения записей
        now = datetime.now(worker.timezone)
        records = worker._get_due_records(now)
        print(f"✅ Получение готовых записей: {len(records)} шт")
        
        # Тест группировки (с пустыми данными)
        batches = worker._group_by_user(records)
        print(f"✅ Группировка по пользователям: {len(batches)} пользователей")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка методов: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_message_formatting():
    """Тест форматирования сообщений"""
    print("\n🔄 Тестирование форматирования сообщений...")
    
    try:
        from app.worker import NotificationWorker
        
        worker = NotificationWorker()
        now = datetime.now(worker.timezone)
        
        # Тестовая запись
        test_record = {
            'task_id': 12345,
            'user_id': 106,
            'last_mention_at': (now - timedelta(hours=5)).isoformat(),
            'last_mention_comment_text': 'Тестовый комментарий с длинным текстом который должен обрезаться'
        }
        
        # Тест одиночного сообщения
        single_msg = worker._format_single_message(test_record, now)
        print(f"✅ Одиночное сообщение:")
        print(f"   {single_msg.split()[0:10]}")  # Первые 10 слов
        
        # Тест батч-сообщения
        multi_msg = worker._format_multi_message([test_record, test_record], now)
        print(f"✅ Батч-сообщение:")
        print(f"   {multi_msg.split()[0:10]}")  # Первые 10 слов
        
        return True
    except Exception as e:
        print(f"❌ Ошибка форматирования: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_single_cycle():
    """Тест одного цикла воркера"""
    print("\n🔄 Тестирование одного цикла...")
    
    try:
        from app.worker import NotificationWorker
        
        worker = NotificationWorker()
        
        # Запускаем один цикл
        await worker._process_cycle()
        print("✅ Один цикл выполнен успешно")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка цикла: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_short_run():
    """Тест короткого запуска воркера (10 секунд)"""
    print("\n🔄 Тестирование короткого запуска (10 сек)...")
    
    try:
        from app.worker import NotificationWorker
        
        worker = NotificationWorker()
        
        # Запускаем воркер в фоне
        worker_task = asyncio.create_task(worker.start())
        
        # Ждем 10 секунд
        await asyncio.sleep(10)
        
        # Останавливаем
        worker.stop()
        
        # Ждем завершения задачи
        try:
            await asyncio.wait_for(worker_task, timeout=2.0)
        except asyncio.TimeoutError:
            worker_task.cancel()
        
        print("✅ Короткий запуск выполнен успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка короткого запуска: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование фонового воркера Этапа 4")
    print("=" * 60)
    
    success = True
    success &= await test_worker_import()
    success &= await test_worker_configuration()
    success &= await test_worker_methods()
    success &= await test_message_formatting()
    success &= await test_single_cycle()
    success &= await test_short_run()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ВСЕ ТЕСТЫ ВОРКЕРА ПРОЙДЕНЫ!")
        print("✅ Воркер корректно импортируется")
        print("✅ Конфигурация загружается")
        print("✅ Методы работают")
        print("✅ Форматирование сообщений функционирует")
        print("✅ Циклы выполняются без ошибок")
        print("\n🔧 Готов к интеграции с API!")
        print("\n📋 Для полного тестирования:")
        print("1. Убедитесь что в БД есть настройка service_enabled=true")
        print("2. Создайте тестовые записи в pending_notifications")
        print("3. Запустите: python -m app.worker")
    else:
        print("❌ Есть проблемы в воркере, нужно их исправить")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
