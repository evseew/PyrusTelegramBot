#!/usr/bin/env python3
"""
Фоновый воркер для отправки уведомлений по расписанию
Этап 4: Планировщик с тихими часами, TTL, батчами
"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pytz
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем наши модули
from .db import db
from .utils import is_in_quiet_hours, schedule_after, remove_at_mentions, calculate_fire_icons

# Конфигурация из переменных окружения
REPEAT_INTERVAL_HOURS = float(os.getenv("REPEAT_INTERVAL_HOURS", "3"))
TTL_HOURS = float(os.getenv("TTL_HOURS", "24"))
TZ = os.getenv("TZ", "Asia/Yekaterinburg")
QUIET_START = os.getenv("QUIET_START", "22:00")
QUIET_END = os.getenv("QUIET_END", "09:00")
TRUNC_TASK_TITLE_LEN = int(os.getenv("TRUNC_TASK_TITLE_LEN", "50"))
TRUNC_COMMENT_LEN = int(os.getenv("TRUNC_COMMENT_LEN", "50"))

# Очистка логов: параметры по умолчанию
LOGS_RETENTION_DAYS = int(os.getenv("LOGS_RETENTION_DAYS", "2"))
LOGS_CLEANUP_INTERVAL_HOURS = int(os.getenv("LOGS_CLEANUP_INTERVAL_HOURS", "24"))

# Режим работы (переключается автоматически при наличии BOT_TOKEN)
DRY_RUN = not bool(os.getenv("BOT_TOKEN"))  # Если есть BOT_TOKEN, используем реальную отправку


class NotificationWorker:
    """Фоновый воркер для обработки очереди уведомлений"""
    
    def __init__(self):
        self.timezone = pytz.timezone(TZ)
        self.running = False
        self.telegram_bot = None
        
        # Импортируем и инициализируем бота только если не DRY_RUN
        if not DRY_RUN:
            try:
                from .bot import bot
                self.telegram_bot = bot
                print(f"✅ Telegram бот инициализирован для отправки уведомлений")
            except Exception as e:
                print(f"⚠️ Ошибка инициализации Telegram бота: {e}")
                print(f"📝 Переключаемся в DRY_RUN режим")
                # Устанавливаем DRY_RUN режим через globals()
                globals()['DRY_RUN'] = True
    
    async def start(self):
        """Запуск воркера с циклом каждые 60 секунд"""
        self.running = True
        print(f"🚀 Воркер запущен (TZ: {TZ}, интервал: 60сек)")
        
        while self.running:
            try:
                await self._process_cycle()
            except Exception as e:
                print(f"❌ Ошибка в цикле воркера: {e}")
                # Логируем ошибку но продолжаем работу
                db.log_event("worker_error", {"error": str(e)})
            
            # Ждем 60 секунд до следующего цикла
            await asyncio.sleep(60)
    
    def stop(self):
        """Остановка воркера"""
        self.running = False
        print("🛑 Воркер остановлен")
    
    async def _process_cycle(self):
        """Один цикл обработки уведомлений"""
        now = datetime.now(self.timezone)
        
        # 1. Проверяем глобальный флаг service_enabled
        if not self._is_service_enabled():
            print(f"⏸️  Сервис отключен (service_enabled=false)")
            return
        
        # 2. Проверяем тихие часы
        if is_in_quiet_hours(now, TZ, QUIET_START, QUIET_END):
            print(f"😴 Тихие часы ({now.strftime('%H:%M')}), пропускаем цикл")
            return
        
        # 3. Выбираем записи готовые к отправке
        due_records = self._get_due_records(now)
        if not due_records:
            print(f"✅ Нет готовых к отправке записей ({now.strftime('%H:%M')})")
            return
        
        print(f"📬 Найдено {len(due_records)} записей к отправке")
        
        # 4. Группируем по пользователям и отправляем батчи
        user_batches = self._group_by_user(due_records)
        
        for user_id, records in user_batches.items():
            await self._send_user_batch(user_id, records, now)
        
        # 5. Обновляем записи (TTL, повторы)
        await self._update_records_after_sending(due_records, now)

        # 6. Периодическая очистка логов в БД по retention
        self._maybe_cleanup_logs(now)
    
    def _is_service_enabled(self) -> bool:
        """Проверка глобального флага service_enabled"""
        try:
            enabled = db.settings_get('service_enabled')
            return enabled == 'true'
        except Exception as e:
            print(f"⚠️ Ошибка проверки настроек: {e}")
            return False  # По умолчанию отключено при ошибке
    
    def _get_due_records(self, now: datetime) -> List[Dict[str, Any]]:
        """Выбор записей готовых к отправке"""
        try:
            # Конвертируем время в UTC для запроса к БД
            now_utc = now.astimezone(pytz.UTC).replace(tzinfo=None)
            return db.select_due(now_utc)
        except Exception as e:
            print(f"⚠️ Ошибка выбора готовых записей: {e}")
            return []
    
    def _group_by_user(self, records: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Группировка записей по пользователям для батч-отправки"""
        batches = {}
        
        for record in records:
            user_id = record['user_id']
            if user_id not in batches:
                batches[user_id] = []
            batches[user_id].append(record)
        
        return batches
    
    async def _send_user_batch(self, user_id: int, records: List[Dict[str, Any]], now: datetime):
        """Отправка батч-сообщения пользователю"""
        try:
            # Получаем данные пользователя
            user_data = records[0].get('users')  # Данные из JOIN запроса
            if not user_data:
                print(f"⚠️ Нет данных пользователя для user_id={user_id}")
                return
            
            telegram_id = user_data.get('telegram_id')
            full_name = user_data.get('full_name', f'User {user_id}')
            
            # Формируем сообщение
            message = self._format_batch_message(records, now)
            
            # В режиме DRY_RUN только логируем
            if DRY_RUN:
                print(f"📝 [DRY RUN] Сообщение для {full_name} (TG:{telegram_id}):")
                print(f"   {message}")
                
                # Логируем в БД
                db.log_event("notify_dry_run", {
                    "user_id": user_id,
                    "telegram_id": telegram_id,
                    "full_name": full_name,
                    "task_count": len(records),
                    "message": message
                })
            else:
                # Реальная отправка через Telegram
                success = await self._send_telegram_message(telegram_id, message)
                
                if success:
                    print(f"✅ Уведомление отправлено {full_name} (TG:{telegram_id})")
                    db.log_event("notify_sent", {
                        "user_id": user_id,
                        "telegram_id": telegram_id,
                        "full_name": full_name,
                        "task_count": len(records)
                    })
                else:
                    print(f"❌ Не удалось отправить уведомление {full_name} (TG:{telegram_id})")
                    db.log_event("notify_failed", {
                        "user_id": user_id,
                        "telegram_id": telegram_id,
                        "full_name": full_name,
                        "task_count": len(records),
                        "error": "telegram_send_failed"
                    })
            
        except Exception as e:
            print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
            db.log_event("notify_error", {
                "user_id": user_id,
                "error": str(e)
            })
    
    def _format_batch_message(self, records: List[Dict[str, Any]], now: datetime) -> str:
        """Форматирование батч-сообщения по PRD"""
        if len(records) == 1:
            # Одиночное сообщение
            return self._format_single_message(records[0], now)
        else:
            # Батч-сообщение
            return self._format_multi_message(records, now)
    
    def _format_single_message(self, record: Dict[str, Any], now: datetime) -> str:
        """Форматирование одиночного сообщения"""
        task_id = record['task_id']
        last_mention_at = datetime.fromisoformat(record['last_mention_at'].replace('Z', '+00:00'))
        
        # Заголовок задачи берём из БД (сохранён при приёме вебхука)
        task_title = record.get('task_title') or f"Задача #{task_id}"
        # Берём предочищенный текст, если он есть (очищен во время приёма вебхука от ФИО упомянутых)
        raw_comment = record.get('last_mention_comment_text_clean') or record.get('last_mention_comment_text', 'Комментарий')
        comment_text = remove_at_mentions(raw_comment)
        
        # Вычисляем просрочку (приводим к одной таймзоне)
        now_utc = now.astimezone(pytz.UTC) if now.tzinfo else pytz.UTC.localize(now)
        last_mention_utc = last_mention_at if last_mention_at.tzinfo else pytz.UTC.localize(last_mention_at)
        hours_overdue = int((now_utc - last_mention_utc).total_seconds() / 3600)
        
        # Обрезаем тексты
        task_title_short = task_title[:TRUNC_TASK_TITLE_LEN]
        comment_short = comment_text[:TRUNC_COMMENT_LEN]
        
        # Рассчитываем количество огоньков
        times_sent = int(record.get('times_sent', 0))
        fire_icons = calculate_fire_icons(hours_overdue, times_sent)
        
        return f"""👋 Привет! У вас есть неотвеченная задача 📋

{fire_icons} 
{task_title_short}
💬 {comment_short}
🔗 https://pyrus.com/t#id{task_id}"""
    
    def _format_multi_message(self, records: List[Dict[str, Any]], now: datetime) -> str:
        """Форматирование батч-сообщения"""
        # Подготавливаем данные для каждой задачи
        task_data = []
        
        for record in records:
            task_id = record['task_id']
            last_mention_at = datetime.fromisoformat(record['last_mention_at'].replace('Z', '+00:00'))
            
            # Заголовок задачи берём из БД (сохранён при приёме вебхука)
            task_title = record.get('task_title') or f"Задача #{task_id}"
            raw_comment = record.get('last_mention_comment_text_clean') or record.get('last_mention_comment_text', 'Комментарий')
            comment_text = remove_at_mentions(raw_comment)
            
            # Вычисляем просрочку (приводим к одной таймзоне)
            now_utc = now.astimezone(pytz.UTC) if now.tzinfo else pytz.UTC.localize(now)
            last_mention_utc = last_mention_at if last_mention_at.tzinfo else pytz.UTC.localize(last_mention_at)
            hours_overdue = int((now_utc - last_mention_utc).total_seconds() / 3600)
            
            # Обрезаем тексты
            task_title_short = task_title[:TRUNC_TASK_TITLE_LEN]
            comment_short = comment_text[:TRUNC_COMMENT_LEN]
            
            # Рассчитываем количество огоньков для сортировки
            times_sent = int(record.get('times_sent', 0))
            fire_icons = calculate_fire_icons(hours_overdue, times_sent)
            fire_level = len(fire_icons)  # Количество огоньков для сортировки
            
            task_data.append({
                'task_id': task_id,
                'task_title_short': task_title_short,
                'comment_short': comment_short,
                'fire_icons': fire_icons,
                'fire_level': fire_level
            })
        
        # Сортируем по убыванию приоритета (больше огоньков = выше приоритет)
        task_data.sort(key=lambda x: x['fire_level'], reverse=True)
        
        # Формируем строки задач
        lines = []
        for task in task_data:
            task_line = f"""{task['fire_icons']} 
{task['task_title_short']}
💬 {task['comment_short']}
🔗 https://pyrus.com/t#id{task['task_id']}"""
            lines.append(task_line)
        
        # Собираем полное сообщение с единым заголовком
        header = "👋 Привет! У вас есть неотвеченная задача 📋\n\n"
        
        return header + '\n\n'.join(lines)
    
    async def _send_telegram_message(self, telegram_id: int, message: str):
        """Отправка сообщения через Telegram"""
        if self.telegram_bot:
            return await self.telegram_bot.send_notification(telegram_id, message)
        else:
            print(f"⚠️ Telegram бот недоступен для отправки в chat {telegram_id}")
            return False
    
    async def _update_records_after_sending(self, records: List[Dict[str, Any]], now: datetime):
        """Обновление записей после отправки (TTL, повторы)"""
        now_utc = now.astimezone(pytz.UTC).replace(tzinfo=None)
        
        for record in records:
            task_id = record['task_id']
            user_id = record['user_id']
            
            try:
                # Используем функцию из db.py для обновления
                db.mark_sent_or_delete_by_ttl(
                    task_id=task_id,
                    user_id=user_id,
                    now_ts=now_utc,
                    ttl_hours=TTL_HOURS,
                    repeat_interval_hours=REPEAT_INTERVAL_HOURS,
                    tz_name=TZ,
                    quiet_start=QUIET_START,
                    quiet_end=QUIET_END
                )
                
            except Exception as e:
                print(f"⚠️ Ошибка обновления записи {task_id}/{user_id}: {e}")

    def _maybe_cleanup_logs(self, now: datetime) -> None:
        """Ежедневная очистка логов по системному времени и маркеру в settings.

        - Храним в settings ключ `logs_last_cleanup_ts` (ISO время в UTC без tz).
        - Если прошло >= LOGS_CLEANUP_INTERVAL_HOURS — вызываем db.cleanup_old_logs(LOGS_RETENTION_DAYS).
        """
        try:
            # Приводим текущее время к UTC naive (совместимо с БД-методами)
            now_utc_naive = now.astimezone(pytz.UTC).replace(tzinfo=None)

            last_cleanup_str = db.settings_get('logs_last_cleanup_ts')
            should_run = True
            if last_cleanup_str:
                try:
                    parsed = datetime.fromisoformat(str(last_cleanup_str).replace('Z', '+00:00'))
                    last_cleanup_utc_naive = (
                        parsed if parsed.tzinfo is None else parsed.astimezone(pytz.UTC).replace(tzinfo=None)
                    )
                    hours_since = (now_utc_naive - last_cleanup_utc_naive).total_seconds() / 3600
                    should_run = hours_since >= LOGS_CLEANUP_INTERVAL_HOURS
                except Exception:
                    # Если не смогли распарсить — запустим очистку и перезапишем метку
                    should_run = True

            if not should_run:
                return

            # Выполняем очистку логов старше retention
            db.cleanup_old_logs(days=LOGS_RETENTION_DAYS)
            db.settings_set('logs_last_cleanup_ts', now_utc_naive.isoformat())
            db.log_event("logs_cleanup", {
                "retention_days": LOGS_RETENTION_DAYS,
                "interval_hours": LOGS_CLEANUP_INTERVAL_HOURS
            })
            print(f"🧹 Очистка логов завершена: retention={LOGS_RETENTION_DAYS}d, next in {LOGS_CLEANUP_INTERVAL_HOURS}h")
        except Exception as e:
            print(f"⚠️ Ошибка очистки логов: {e}")


# Функция для запуска воркера
async def run_worker():
    """Запуск фонового воркера"""
    worker = NotificationWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки")
        worker.stop()
    except Exception as e:
        print(f"❌ Критическая ошибка воркера: {e}")
        worker.stop()


# Точка входа для запуска
if __name__ == "__main__":
    print("🚀 Запуск фонового воркера уведомлений")
    print(f"📅 Режим: DRY_RUN={DRY_RUN}")
    print(f"🕐 Часовой пояс: {TZ}")
    print(f"😴 Тихие часы: {QUIET_START}-{QUIET_END}")
    print(f"🔄 Интервал повторов: {REPEAT_INTERVAL_HOURS}ч")
    print(f"⏰ TTL: {TTL_HOURS}ч")
    print("─" * 50)
    
    asyncio.run(run_worker())
