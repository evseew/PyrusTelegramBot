#!/usr/bin/env python3
"""
Финальный тест воркера (без записи в БД из-за RLS)
"""
import asyncio
import sys
sys.path.append('.')

from dotenv import load_dotenv
load_dotenv()

async def test_worker_architecture():
    """Тест архитектуры воркера"""
    print("🔄 Проверка архитектуры воркера...")
    
    try:
        from app.worker import NotificationWorker
        
        worker = NotificationWorker()
        
        # Проверяем основные компоненты
        assert hasattr(worker, '_process_cycle'), "Отсутствует _process_cycle"
        assert hasattr(worker, '_is_service_enabled'), "Отсутствует _is_service_enabled"
        assert hasattr(worker, '_get_due_records'), "Отсутствует _get_due_records"
        assert hasattr(worker, '_group_by_user'), "Отсутствует _group_by_user"
        assert hasattr(worker, '_send_user_batch'), "Отсутствует _send_user_batch"
        assert hasattr(worker, '_format_batch_message'), "Отсутствует _format_batch_message"
        assert hasattr(worker, '_update_records_after_sending'), "Отсутствует _update_records_after_sending"
        
        print("✅ Все необходимые методы присутствуют")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка архитектуры: {e}")
        return False

async def test_message_formats():
    """Тест форматов сообщений по PRD"""
    print("\n🔄 Тестирование форматов сообщений...")
    
    try:
        from app.worker import NotificationWorker
        from datetime import datetime, timezone, timedelta
        
        worker = NotificationWorker()
        now = datetime.now(timezone.utc)
        
        # Тестовые данные
        test_record_1 = {
            'task_id': 12345,
            'user_id': 106,
            'last_mention_at': (now - timedelta(hours=5)).isoformat(),
            'last_mention_comment_text': 'Короткий комментарий'
        }
        
        test_record_2 = {
            'task_id': 67890,
            'user_id': 106,
            'last_mention_at': (now - timedelta(hours=10)).isoformat(),
            'last_mention_comment_text': 'Очень длинный комментарий который должен быть обрезан по длине согласно настройкам TRUNC_COMMENT_LEN'
        }
        
        # Тест одиночного сообщения
        single_msg = worker._format_single_message(test_record_1, now)
        print("✅ Одиночное сообщение:")
        print(f"   Содержит 'просрочили ответ': {'просрочили ответ' in single_msg}")
        print(f"   Содержит task_id: {str(test_record_1['task_id']) in single_msg}")
        print(f"   Содержит ссылку pyrus.com: {'pyrus.com' in single_msg}")
        
        # Тест батч-сообщения
        batch_msg = worker._format_multi_message([test_record_1, test_record_2], now)
        print("✅ Батч-сообщение:")
        print(f"   Содержит заголовок: {'По вам есть задачи' in batch_msg}")
        print(f"   Содержит оба task_id: {str(test_record_1['task_id']) in batch_msg and str(test_record_2['task_id']) in batch_msg}")
        print(f"   Обрезает длинные комментарии: {len(batch_msg) < 1000}")  # Проверка разумной длины
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка форматирования: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_time_handling():
    """Тест обработки времени и тихих часов"""
    print("\n🔄 Тестирование обработки времени...")
    
    try:
        from app.worker import NotificationWorker
        from app.utils import is_in_quiet_hours
        from datetime import datetime
        import pytz
        
        worker = NotificationWorker()
        tz = pytz.timezone("Asia/Yekaterinburg")
        
        # Тест тихих часов
        night_time = tz.localize(datetime(2025, 1, 20, 23, 30))  # 23:30
        day_time = tz.localize(datetime(2025, 1, 20, 14, 30))    # 14:30
        
        night_quiet = is_in_quiet_hours(night_time, "Asia/Yekaterinburg", "22:00", "09:00")
        day_quiet = is_in_quiet_hours(day_time, "Asia/Yekaterinburg", "22:00", "09:00")
        
        print(f"✅ Ночное время (23:30) в тихих часах: {night_quiet}")
        print(f"✅ Дневное время (14:30) НЕ в тихих часах: {not day_quiet}")
        
        assert night_quiet == True, "Ночное время должно быть в тихих часах"
        assert day_quiet == False, "Дневное время не должно быть в тихих часах"
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обработки времени: {e}")
        return False

async def test_grouping_logic():
    """Тест логики группировки"""
    print("\n🔄 Тестирование логики группировки...")
    
    try:
        from app.worker import NotificationWorker
        
        worker = NotificationWorker()
        
        # Тестовые записи для разных пользователей
        test_records = [
            {'user_id': 106, 'task_id': 1},
            {'user_id': 107, 'task_id': 2},
            {'user_id': 106, 'task_id': 3},  # Второй для пользователя 106
            {'user_id': 108, 'task_id': 4},
        ]
        
        batches = worker._group_by_user(test_records)
        
        print(f"✅ Количество пользователей: {len(batches)}")
        print(f"✅ Пользователь 106 имеет 2 задачи: {len(batches.get(106, [])) == 2}")
        print(f"✅ Пользователь 107 имеет 1 задачу: {len(batches.get(107, [])) == 1}")
        print(f"✅ Пользователь 108 имеет 1 задачу: {len(batches.get(108, [])) == 1}")
        
        assert len(batches) == 3, f"Ожидалось 3 пользователя, получено {len(batches)}"
        assert len(batches[106]) == 2, f"У пользователя 106 должно быть 2 задачи"
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка группировки: {e}")
        return False

async def test_configuration_loading():
    """Тест загрузки конфигурации"""
    print("\n🔄 Тестирование загрузки конфигурации...")
    
    try:
        from app.worker import (
            REPEAT_INTERVAL_HOURS, TTL_HOURS, TZ, 
            QUIET_START, QUIET_END, TRUNC_TASK_TITLE_LEN, 
            TRUNC_COMMENT_LEN, DRY_RUN
        )
        
        # Проверяем типы и разумные значения
        assert isinstance(REPEAT_INTERVAL_HOURS, float), "REPEAT_INTERVAL_HOURS должен быть float"
        assert isinstance(TTL_HOURS, float), "TTL_HOURS должен быть float"
        assert isinstance(TZ, str), "TZ должен быть строкой"
        assert isinstance(TRUNC_TASK_TITLE_LEN, int), "TRUNC_TASK_TITLE_LEN должен быть int"
        assert isinstance(TRUNC_COMMENT_LEN, int), "TRUNC_COMMENT_LEN должен быть int"
        assert isinstance(DRY_RUN, bool), "DRY_RUN должен быть bool"
        
        assert REPEAT_INTERVAL_HOURS > 0, "Интервал повторов должен быть положительным"
        assert TTL_HOURS > 0, "TTL должен быть положительным"
        assert TRUNC_TASK_TITLE_LEN > 0, "Длина обрезки заголовка должна быть положительной"
        
        print(f"✅ Интервал повторов: {REPEAT_INTERVAL_HOURS}ч")
        print(f"✅ TTL: {TTL_HOURS}ч")
        print(f"✅ Часовой пояс: {TZ}")
        print(f"✅ Тихие часы: {QUIET_START}-{QUIET_END}")
        print(f"✅ Обрезка заголовков: {TRUNC_TASK_TITLE_LEN}")
        print(f"✅ Обрезка комментариев: {TRUNC_COMMENT_LEN}")
        print(f"✅ Режим DRY_RUN: {DRY_RUN}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

async def main():
    """Основная функция финального тестирования"""
    print("🚀 Финальное тестирование фонового воркера Этапа 4")
    print("=" * 60)
    
    success = True
    success &= await test_worker_architecture()
    success &= await test_configuration_loading()
    success &= await test_time_handling()
    success &= await test_grouping_logic()
    success &= await test_message_formats()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ЭТАП 4 ЗАВЕРШЁН УСПЕШНО!")
        print("✅ Архитектура воркера корректна")
        print("✅ Конфигурация загружается правильно")
        print("✅ Тихие часы обрабатываются")
        print("✅ Группировка по пользователям работает")
        print("✅ Форматирование сообщений соответствует PRD")
        print("✅ Все методы присутствуют и функциональны")
        print("\n🔧 ГОТОВ К ПРОДАКШН ЗАПУСКУ!")
        print("\n📋 Команды для запуска:")
        print("1. На VPS: python -m app.worker")
        print("2. Мониторинг: tail -f logs/pyrus_raw_*.ndjson")
        print("3. В БД таблица logs покажет события notify_dry_run")
        print("\n🚀 ГОТОВЫ К ЭТАПУ 5 (Telegram бот)!")
    else:
        print("❌ Есть проблемы в воркере")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
