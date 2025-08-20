"""
Обёртки для работы с базой данных (Supabase)
"""
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from .models import User, PendingNotification


class DatabaseError(Exception):
    """Ошибка работы с базой данных"""
    pass


class Database:
    """Класс для работы с Supabase"""
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise DatabaseError("SUPABASE_URL и SUPABASE_KEY должны быть установлены")
        
        # Создаём клиент с базовыми настройками
        try:
            self.client: Client = create_client(supabase_url, supabase_key)
        except Exception as e:
            raise DatabaseError(f"Ошибка создания Supabase клиента: {e}")
    
    # === Работа с пользователями ===
    
    def upsert_user(self, user_id: int, telegram_id: int, phone: Optional[str] = None, 
                   full_name: Optional[str] = None) -> User:
        """
        Создать или обновить пользователя
        
        Args:
            user_id: ID пользователя в Pyrus
            telegram_id: Telegram chat_id
            phone: Телефон в формате E.164
            full_name: ФИО
            
        Returns:
            Объект пользователя
        """
        data = {
            "user_id": user_id,
            "telegram_id": telegram_id,
            "phone": phone,
            "full_name": full_name,
            "updated_at": datetime.now().isoformat()
        }
        
        result = self.client.table("users").upsert(data).execute()
        
        if not result.data:
            raise DatabaseError("Ошибка при сохранении пользователя")
        
        return User(**result.data[0])
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Получить пользователя по Pyrus user_id
        
        Args:
            user_id: ID пользователя в Pyrus
            
        Returns:
            Объект пользователя или None
        """
        result = self.client.table("users").select("*").eq("user_id", user_id).execute()
        
        if not result.data:
            return None
        
        return User(**result.data[0])
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получить пользователя по Telegram ID
        """
        result = self.client.table("users").select("*").eq("telegram_id", telegram_id).execute()
        
        if not result.data:
            return None
        
        return User(**result.data[0])
    
    def get_all_users(self) -> List[User]:
        """Получить всех зарегистрированных пользователей"""
        result = self.client.table("users").select("*").execute()
        return [User(**row) for row in result.data]
    
    # === Работа с очередью уведомлений ===
    
    def upsert_or_shift_pending(self, task_id: int, user_id: int, mention_ts: datetime,
                               comment_id: int, comment_text: str, next_send_at: datetime) -> None:
        """
        Создать или обновить запись в очереди уведомлений
        
        Args:
            task_id: ID задачи
            user_id: ID пользователя
            mention_ts: Время упоминания
            comment_id: ID комментария
            comment_text: Текст комментария
            next_send_at: Время следующей отправки
        """
        # Проверяем, есть ли уже запись
        existing = self.client.table("pending_notifications").select("*").eq("task_id", task_id).eq("user_id", user_id).execute()
        
        if existing.data:
            # Обновляем существующую запись
            data = {
                "last_mention_at": mention_ts.isoformat(),
                "last_mention_comment_id": comment_id,
                "last_mention_comment_text": comment_text,
                "next_send_at": next_send_at.isoformat()
            }
            self.client.table("pending_notifications").update(data).eq("task_id", task_id).eq("user_id", user_id).execute()
        else:
            # Создаём новую запись
            data = {
                "task_id": task_id,
                "user_id": user_id,
                "first_mention_at": mention_ts.isoformat(),
                "last_mention_at": mention_ts.isoformat(),
                "last_mention_comment_id": comment_id,
                "last_mention_comment_text": comment_text,
                "next_send_at": next_send_at.isoformat(),
                "times_sent": 0
            }
            self.client.table("pending_notifications").insert(data).execute()
    
    def delete_pending(self, task_id: int, user_id: int) -> None:
        """Удалить запись из очереди для конкретного пользователя"""
        self.client.table("pending_notifications").delete().eq("task_id", task_id).eq("user_id", user_id).execute()
    
    def delete_pending_by_task(self, task_id: int) -> None:
        """Удалить все записи очереди для задачи"""
        self.client.table("pending_notifications").delete().eq("task_id", task_id).execute()
    
    def select_due(self, now_ts: datetime) -> List[Dict[str, Any]]:
        """
        Выбрать записи, готовые к отправке
        
        Args:
            now_ts: Текущее время
            
        Returns:
            Список записей с данными пользователя
        """
        # Джойн с таблицей users для получения telegram_id
        result = self.client.table("pending_notifications").select("""
            *,
            users!inner(telegram_id, full_name)
        """).lte("next_send_at", now_ts.isoformat()).execute()
        
        return result.data
    
    def mark_sent_or_delete_by_ttl(self, task_id: int, user_id: int, now_ts: datetime, 
                                  ttl_hours: int, repeat_interval_hours: int,
                                  tz_name: str, quiet_start: str, quiet_end: str) -> None:
        """
        Обновить запись после отправки или удалить по TTL
        
        Args:
            task_id: ID задачи
            user_id: ID пользователя  
            now_ts: Текущее время
            ttl_hours: TTL в часах
            repeat_interval_hours: Интервал повторов
            tz_name: Часовой пояс
            quiet_start: Начало тихих часов
            quiet_end: Конец тихих часов
        """
        from .utils import schedule_after
        
        # Получаем текущую запись
        result = self.client.table("pending_notifications").select("*").eq("task_id", task_id).eq("user_id", user_id).execute()
        
        if not result.data:
            return
        
        row = result.data[0]
        last_mention_at = datetime.fromisoformat(row["last_mention_at"].replace('Z', '+00:00'))
        
        # Проверяем TTL
        if now_ts >= last_mention_at + timedelta(hours=ttl_hours):
            # Удаляем по TTL
            self.delete_pending(task_id, user_id)
        else:
            # Обновляем для следующей отправки
            next_send_at = schedule_after(now_ts, repeat_interval_hours, tz_name, quiet_start, quiet_end)
            data = {
                "times_sent": row["times_sent"] + 1,
                "next_send_at": next_send_at.isoformat()
            }
            self.client.table("pending_notifications").update(data).eq("task_id", task_id).eq("user_id", user_id).execute()
    
    # === Идемпотентность комментариев ===
    
    def processed_comment_exists(self, task_id: int, comment_id: int) -> bool:
        """Проверить, обработан ли уже комментарий"""
        result = self.client.table("processed_comments").select("comment_id").eq("task_id", task_id).eq("comment_id", comment_id).execute()
        return len(result.data) > 0
    
    def insert_processed_comment(self, task_id: int, comment_id: int) -> None:
        """Отметить комментарий как обработанный"""
        data = {
            "task_id": task_id,
            "comment_id": comment_id,
            "processed_at": datetime.now().isoformat()
        }
        self.client.table("processed_comments").insert(data).execute()
    
    # === Настройки ===
    
    def settings_get(self, key: str) -> Optional[str]:
        """Получить значение настройки"""
        result = self.client.table("settings").select("value").eq("key", key).execute()
        return result.data[0]["value"] if result.data else None
    
    def settings_set(self, key: str, value: str) -> None:
        """Установить значение настройки"""
        data = {"key": key, "value": value}
        self.client.table("settings").upsert(data).execute()
    
    # === Логирование ===
    
    def log_event(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Записать событие в лог"""
        data = {
            "event": event,
            "payload": payload or {},
            "ts": datetime.now().isoformat()
        }
        self.client.table("logs").insert(data).execute()
    
    # === Очистка ===
    
    def cleanup_old_processed_comments(self, days: int = 7) -> None:
        """Удалить старые обработанные комментарии"""
        cutoff = datetime.now() - timedelta(days=days)
        self.client.table("processed_comments").delete().lt("processed_at", cutoff.isoformat()).execute()
    
    def cleanup_old_logs(self, days: int = 30) -> None:
        """Удалить старые логи"""
        cutoff = datetime.now() - timedelta(days=days)
        self.client.table("logs").delete().lt("ts", cutoff.isoformat()).execute()
    
    # === Статистика для админов ===
    
    def get_queue_stats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получить топ пользователей с максимальной просрочкой
        
        Args:
            limit: Количество записей
            
        Returns:
            Список со статистикой по пользователям
        """
        # В реальном SQL это было бы сложнее, но Supabase позволяет использовать функции
        result = self.client.table("pending_notifications").select("""
            user_id,
            users!inner(full_name),
            last_mention_at,
            count:task_id
        """).execute()
        
        # Обрабатываем результат в Python (в продакшене лучше сделать stored procedure)
        stats = {}
        now = datetime.now()
        
        for row in result.data:
            user_id = row["user_id"]
            last_mention = datetime.fromisoformat(row["last_mention_at"].replace('Z', '+00:00'))
            hours_overdue = (now - last_mention).total_seconds() / 3600
            
            if user_id not in stats:
                stats[user_id] = {
                    "user_id": user_id,
                    "full_name": row["users"]["full_name"] if row["users"] else f"User {user_id}",
                    "max_hours_overdue": hours_overdue,
                    "task_count": 0
                }
            
            stats[user_id]["task_count"] += 1
            stats[user_id]["max_hours_overdue"] = max(stats[user_id]["max_hours_overdue"], hours_overdue)
        
        # Сортируем по максимальной просрочке
        sorted_stats = sorted(stats.values(), key=lambda x: x["max_hours_overdue"], reverse=True)
        
        return sorted_stats[:limit]


# Глобальный экземпляр базы данных
db = Database()
