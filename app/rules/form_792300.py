"""
Правила проверки для формы 792300 (БПЗ).

Правила основаны на реальных требованиях к форме.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

# ID полей формы 792300 (реальные)
TEACHER_ID = 142           # Преподаватель
DATE_BPZ_ID = 220         # Дата БПЗ
ATTENDED_FIRST_ID = 183   # Пришел на 1ое занятие?
GROUP_FIT_ID = 185        # Группа подходит?
DATE_SECOND_ID = 197      # Дата 2го занятия
ATTENDED_SECOND_ID = 198  # Пришел на 2ое занятие?
NEEDED_GROUP_TEXT_ID = 155  # Какая группа нужна?
INVITED_GROUP_TEXT_ID = 242 # В какую группу пригласили?
INVITED_DATE_ID = 243     # На какую дату пригласили?


def _name(fields_meta: Dict[int, Dict[str, Any]], field_id: int, fallback: str) -> str:
    meta = fields_meta.get(field_id) or {}
    return str(meta.get("name") or fallback)


def _get_field_value(field_list: List[Dict[str, Any]], field_id: int) -> Optional[Any]:
    """Ищет значение поля по id, рекурсивно обходя вложенные секции."""
    for f in field_list or []:
        if f.get("id") == field_id:
            return f.get("value")
        val = f.get("value")
        if isinstance(val, dict) and isinstance(val.get("fields"), list):
            nested = _get_field_value(val.get("fields") or [], field_id)
            if nested is not None:
                return nested
    return None


def _as_date_str(value: Any) -> Optional[str]:
    """Конвертирует дату в формат YYYY-MM-DD. Учитывает формат дд.мм.гггг из Pyrus."""
    if value is None:
        return None
    
    # Строковое значение
    if isinstance(value, str):
        date_str = value.strip()
        # Проверяем формат дд.мм.гггг
        if '.' in date_str and len(date_str) == 10:
            try:
                day, month, year = date_str.split('.')
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except (ValueError, IndexError):
                pass
        # Уже в формате YYYY-MM-DD
        return date_str[:10]
    
    # Объект с датой
    if isinstance(value, dict):
        v = value.get("date") or value.get("value") or value.get("text")
        if isinstance(v, str):
            return _as_date_str(v)  # Рекурсивно обрабатываем
    
    return None


def _is_empty_choice(value: Any) -> bool:
    """Проверяет, пустой ли выбор в поле."""
    if value is None:
        return True
    if isinstance(value, str):
        return len(value.strip()) == 0
    if isinstance(value, bool):
        return False  # Булево значение — это осознанный выбор
    if isinstance(value, dict):
        if value.get("checkmark") in ("checked", "unchecked"):
            return False  # Чекбокс отмечен или явно не отмечен
        if value.get("values") in (None, []):
            return True
        # Проверяем choice_names
        choice_names = value.get("choice_names")
        if isinstance(choice_names, list):
            return len(choice_names) == 0
        # Проверяем text/value/name
        text_val = value.get("text") or value.get("value") or value.get("name")
        if isinstance(text_val, str):
            return len(text_val.strip()) == 0
    if isinstance(value, list):
        return len(value) == 0
    return False


def _text_equals(value: Any, target: str) -> bool:
    """Проверяет равенство текстового значения с целевым (без учета регистра)."""
    if value is None:
        return False
    
    target_lower = target.strip().lower()
    
    if isinstance(value, str):
        return value.strip().lower() == target_lower
    
    if isinstance(value, bool):
        normalized = "да" if value else "нет"
        return normalized == target_lower
    
    if isinstance(value, dict):
        # Чекбокс
        if "checkmark" in value:
            ck = str(value.get("checkmark") or "").strip().lower()
            as_text = "да" if ck == "checked" else "нет" if ck == "unchecked" else ""
            if as_text:
                return as_text == target_lower
        
        # choice_names (множественный выбор)
        choice_names = value.get("choice_names")
        if isinstance(choice_names, list):
            return any(isinstance(c, str) and c.strip().lower() == target_lower for c in choice_names)
        
        # Обычные текстовые поля
        text = value.get("text") or value.get("value") or value.get("name")
        if isinstance(text, str):
            return text.strip().lower() == target_lower
    
    return False


def _extract_teacher_full_name(task_fields: List[Dict[str, Any]], field_id: int = TEACHER_ID) -> str:
    """Извлекает ФИО преподавателя из поля справочника сотрудников."""
    v = _get_field_value(task_fields, field_id)
    if isinstance(v, dict):
        # Для справочника сотрудников обычно есть поле text или name
        return str(v.get("text") or v.get("name") or v.get("value") or "").strip()
    if isinstance(v, str):
        return v.strip()
    return ""


def _extract_teacher_user_id(task_fields: List[Dict[str, Any]], field_id: int = TEACHER_ID) -> int | None:
    """Извлекает Pyrus user_id преподавателя из справочника."""
    v = _get_field_value(task_fields, field_id)
    if isinstance(v, dict):
        for k in ("id", "user_id", "value"):
            val = v.get(k)
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return None


def check_rules(fields_meta: Dict[int, Dict[str, Any]], task_fields: List[Dict[str, Any]], target_day: str, run_slot: str) -> Dict[str, List[str]]:
    """
    Проверить все правила формы 792300 для target_day.
    
    Args:
        fields_meta: Метаданные полей формы
        task_fields: Поля конкретной задачи
        target_day: Целевая дата в формате YYYY-MM-DD
        run_slot: Слот запуска (today21 или yesterday12)
    
    Returns:
        Словарь с ошибками: {"general": [...]}
    """
    errors_general: List[str] = []

    # Имена полей для сообщений
    n_teacher = _name(fields_meta, TEACHER_ID, "Преподаватель")
    n_date_bpz = _name(fields_meta, DATE_BPZ_ID, "Дата БПЗ")
    n_att_first = _name(fields_meta, ATTENDED_FIRST_ID, "Пришел на 1ое занятие?")
    n_group_fit = _name(fields_meta, GROUP_FIT_ID, "Группа подходит?")
    n_date_second = _name(fields_meta, DATE_SECOND_ID, "Дата 2го занятия")
    n_att_second = _name(fields_meta, ATTENDED_SECOND_ID, "Пришел на 2ое занятие?")
    n_needed_group = _name(fields_meta, NEEDED_GROUP_TEXT_ID, "Какая группа нужна? Напишите подробно")
    n_invited_group = _name(fields_meta, INVITED_GROUP_TEXT_ID, "В какую группу пригласили?")
    n_invited_date = _name(fields_meta, INVITED_DATE_ID, "На какую дату пригласили?")

    # Значения полей
    v_date_bpz = _as_date_str(_get_field_value(task_fields, DATE_BPZ_ID))
    v_att_first = _get_field_value(task_fields, ATTENDED_FIRST_ID)
    v_group_fit = _get_field_value(task_fields, GROUP_FIT_ID)
    v_date_second = _as_date_str(_get_field_value(task_fields, DATE_SECOND_ID))
    v_att_second = _get_field_value(task_fields, ATTENDED_SECOND_ID)
    v_needed_group = _get_field_value(task_fields, NEEDED_GROUP_TEXT_ID)
    v_invited_group = _get_field_value(task_fields, INVITED_GROUP_TEXT_ID)
    v_invited_date = _as_date_str(_get_field_value(task_fields, INVITED_DATE_ID))

    # ПРАВИЛО 1: Если дата БПЗ = target_day, то должно быть отмечено посещение первого занятия
    if v_date_bpz == target_day and _is_empty_choice(v_att_first):
        errors_general.append(f"«{n_date_bpz}» — сегодня; «{n_att_first}» не отмечено.")

    # ПРАВИЛО 2: Если пришел на первое (ДА) и дата БПЗ сегодня, то нужно заполнить "группа подходит" и "дата 2го"
    if v_date_bpz == target_day and _text_equals(v_att_first, "ДА"):
        if _is_empty_choice(v_group_fit):
            errors_general.append(f"«{n_att_first}» = ДА; нужно выбрать вариант в «{n_group_fit}».")
        if not v_date_second:
            errors_general.append(f"«{n_att_first}» = ДА; заполните «{n_date_second}».")

    # ПРАВИЛО 3: Если НЕ пришел на первое и дата БПЗ сегодня, то нужно заполнить поля приглашения
    if v_date_bpz == target_day and _text_equals(v_att_first, "НЕТ"):
        if not v_needed_group or (isinstance(v_needed_group, str) and len(v_needed_group.strip()) == 0):
            errors_general.append(f"«{n_att_first}» = НЕТ; заполните «{n_needed_group}».")
        if not v_invited_group or (isinstance(v_invited_group, str) and len(v_invited_group.strip()) == 0):
            errors_general.append(f"«{n_att_first}» = НЕТ; заполните «{n_invited_group}».")
        if not v_invited_date:
            errors_general.append(f"«{n_att_first}» = НЕТ; заполните «{n_invited_date}».")
        elif v_invited_date <= target_day:
            errors_general.append(f"«{n_invited_date}» должна быть позже, чем {target_day}.")

    # ПРАВИЛО 4: Если дата 2го занятия = target_day, то должно быть отмечено посещение
    if v_date_second == target_day and _is_empty_choice(v_att_second):
        errors_general.append(f"«{n_date_second}» — сегодня; «{n_att_second}» не отмечено.")

    return {"general": errors_general}
