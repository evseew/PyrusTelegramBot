"""
Утилитарные функции для работы с Pyrus webhook и планированием уведомлений
"""
import hmac
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional
import pytz


def verify_pyrus_signature(raw_body: bytes, secret: str, dev_skip: bool = False, signature_header: str = "") -> bool:
    """
    Проверка подписи HMAC-SHA1 от Pyrus
    
    Args:
        raw_body: Сырое тело запроса
        secret: Секрет интеграции PYRUS_WEBHOOK_SECRET
        dev_skip: Пропустить проверку для разработки
        signature_header: Заголовок X-Pyrus-Sig от Pyrus
    
    Returns:
        True если подпись валидна или dev_skip=True
    """
    if dev_skip:
        return True
    
    if not secret or not signature_header:
        return False
    
    # Pyrus отправляет подпись в заголовке X-Pyrus-Sig
    # Возможные форматы: "sha1=<hex>" и просто "<hex>" (верхний/нижний регистр допускается)
    provided = signature_header.strip()
    provided_lower = provided.lower()
    if provided_lower.startswith("sha1="):
        provided_hex = provided_lower.split("=", 1)[1]
    else:
        provided_hex = provided_lower
    
    expected_hex = hmac.new(
        secret.encode('utf-8'),
        raw_body,
        hashlib.sha1
    ).hexdigest().lower()
    
    # Сравниваем подписи безопасным способом
    return hmac.compare_digest(expected_hex, provided_hex)


def normalize_phone_e164(phone: str) -> Optional[str]:
    """
    Нормализация телефона в формат E.164
    
    Args:
        phone: Номер телефона в любом формате
        
    Returns:
        Номер в формате E.164 или None если невалидный
    """
    if not phone:
        return None
    
    # Удаляем всё кроме цифр и +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Если начинается с 8, заменяем на +7 (Россия)
    if clean_phone.startswith('8'):
        clean_phone = '+7' + clean_phone[1:]
    
    # Если начинается с 7 (без +), добавляем +
    elif clean_phone.startswith('7') and len(clean_phone) == 11:
        clean_phone = '+' + clean_phone
    
    # Если нет кода страны, считаем что Россия
    elif clean_phone.startswith('9') and len(clean_phone) == 10:
        clean_phone = '+7' + clean_phone
    
    # Проверяем что результат похож на валидный номер
    if not clean_phone.startswith('+') or len(clean_phone) < 10:
        return None
    
    return clean_phone


def is_in_quiet_hours(
    dt: datetime, 
    tz_name: str = "Asia/Yekaterinburg",
    quiet_start: str = "22:00",
    quiet_end: str = "09:00"
) -> bool:
    """
    Проверяет, попадает ли время в "тихие часы"
    
    Args:
        dt: Время для проверки (UTC или с таймзоной)
        tz_name: Название таймзоны
        quiet_start: Время начала тихих часов (HH:MM)
        quiet_end: Время окончания тихих часов (HH:MM)
        
    Returns:
        True если время в тихих часах
    """
    tz = pytz.timezone(tz_name)
    
    # Конвертируем в нужную таймзону
    if dt.tzinfo is None:
        # Если UTC без таймзоны
        dt = pytz.UTC.localize(dt)
    dt_local = dt.astimezone(tz)
    
    # Парсим время
    start_hour, start_min = map(int, quiet_start.split(':'))
    end_hour, end_min = map(int, quiet_end.split(':'))
    
    current_time = dt_local.time()
    quiet_start_time = datetime.min.time().replace(hour=start_hour, minute=start_min)
    quiet_end_time = datetime.min.time().replace(hour=end_hour, minute=end_min)
    
    # Если quiet_end меньше quiet_start, значит интервал переходит через полночь
    if quiet_end_time <= quiet_start_time:
        # 22:00-09:00 - тихие часы переходят через полночь
        return current_time >= quiet_start_time or current_time < quiet_end_time
    else:
        # Обычный интервал в рамках одного дня
        return quiet_start_time <= current_time < quiet_end_time


def schedule_after(
    base_ts: datetime,
    hours: float,
    tz_name: str = "Asia/Yekaterinburg", 
    quiet_start: str = "22:00",
    quiet_end: str = "09:00"
) -> datetime:
    """
    Планирует время отправки с учётом тихих часов
    
    Args:
        base_ts: Базовое время (от которого отсчитываем)
        hours: Количество часов для добавления
        tz_name: Название таймзоны
        quiet_start: Время начала тихих часов
        quiet_end: Время окончания тихих часов
        
    Returns:
        Время отправки с учётом тихих часов (в UTC без timezone)
    """
    tz = pytz.timezone(tz_name)
    
    # Обеспечиваем что base_ts имеет таймзону
    if base_ts.tzinfo is None:
        base_ts = pytz.UTC.localize(base_ts)
    
    # Добавляем часы к базовому времени
    scheduled_time = base_ts + timedelta(hours=hours)
    
    # Если попадаем в тихие часы, переносим на конец тихих часов
    if is_in_quiet_hours(scheduled_time, tz_name, quiet_start, quiet_end):
        # Конвертируем в локальную таймзону
        local_time = scheduled_time.astimezone(tz)
        
        # Находим следующий день и устанавливаем время окончания тихих часов
        end_hour, end_min = map(int, quiet_end.split(':'))
        
        # Если тихие часы заканчиваются завтра (например, 22:00-09:00)
        start_hour, _ = map(int, quiet_start.split(':'))
        if end_hour <= start_hour:
            # Если сейчас после quiet_start, то берём завтрашний quiet_end
            if local_time.hour >= start_hour:
                next_day = local_time.date() + timedelta(days=1)
            else:
                # Если сейчас до quiet_end, то сегодняшний quiet_end
                next_day = local_time.date()
        else:
            # Тихие часы в рамках одного дня
            next_day = local_time.date() + timedelta(days=1)
        
        # Устанавливаем время окончания тихих часов
        end_time = tz.localize(
            datetime.combine(next_day, datetime.min.time().replace(hour=end_hour, minute=end_min))
        )
        
        # Конвертируем в UTC и убираем таймзону
        scheduled_time = end_time.astimezone(pytz.UTC).replace(tzinfo=None)
    else:
        # Если не в тихих часах, просто убираем таймзону из результата
        scheduled_time = scheduled_time.astimezone(pytz.UTC).replace(tzinfo=None)
    
    return scheduled_time


def remove_at_mentions(text: str) -> str:
    """
    Удаляет упоминания вида @Имя или @ИмяФамилия из текста комментария.
    Если после удаления текст пустой или состоит из пробелов/знаков пунктуации —
    возвращает строку "(без текста)".
    """
    if not text:
        return "(без текста)"
    import re
    # Удаляем токены, начинающиеся с '@' и состоящие из букв/цифр/нижнего подчёркивания/дефиса/точки
    cleaned = re.sub(r"@([\w\-\.]+)", "", text, flags=re.UNICODE)
    # Схлопываем повторяющиеся пробелы и обрезаем
    cleaned = re.sub(r"\s+", " ", cleaned, flags=re.UNICODE).strip()
    # Если после удаления ничего осмысленного не осталось — подставляем заглушку
    if not cleaned:
        return "(без текста)"
    return cleaned


def remove_full_names(text: str, full_names: list[str]) -> str:
    """
    Удаляет из текста точные вхождения ФИО из списка full_names.
    - Чувствительно к регистру (как в БД), но устойчиво к множественным пробелам.
    - После удаления схлопывает пробелы; если пусто — возвращает "(без текста)".
    """
    if not text:
        return "(без текста)"
    cleaned = text
    import re
    for name in full_names:
        if not name:
            continue
        # Экранируем имя для regex, заменяем группы пробелов на \s+
        escaped = re.escape(name)
        # Приводим повторяющиеся пробелы в имени к шаблону \s+
        pattern = re.sub(r"\\\s+", r"\\s+", escaped)
        cleaned = re.sub(pattern, "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned, flags=re.UNICODE).strip()
    return cleaned or "(без текста)"
