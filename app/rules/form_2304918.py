"""
Правила проверки для формы 2304918.

Функции принимают:
- form_fields_by_id: dict[id -> {name, type}] — словарь метаданных полей формы
- task_fields: список полей задачи из реестра (как в Pyrus register)
- target_day: строка YYYY-MM-DD (локальная дата) — день проверки (сегодня/вчера)

Возвращают список строк-человеческих описаний нарушений, используя реальные
названия полей из form_fields_by_id.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# Полезные ID полей (константы для читаемости)
TEACHER_ID = 8
DATE_1_ID = 26
ATTENDED_1_ID = 27
DATE_OTHER_GROUP_ID = 31
ATTENDED_OTHER_GROUP_ID = 32
FIRST_LESSON_DATE_ID = 47
ATTENDED_FIRST_ID = 50
GROUP_FIT_ID = 53
SECOND_LESSON_DATE_ID = 56
ATTENDED_SECOND_ID = 57
EXIT_STATUS_ID = 25
NEXT_CONTACT_DATE_ID = 41


def _name(fields_meta: Dict[int, Dict[str, Any]], field_id: int, fallback: str) -> str:
    meta = fields_meta.get(field_id) or {}
    return str(meta.get("name") or fallback)


def _get_field_value(field_list: List[Dict[str, Any]], field_id: int) -> Optional[Any]:
    for f in field_list:
        if f.get("id") == field_id:
            return f.get("value")
    return None


def _as_date_str(value: Any) -> Optional[str]:
    # В Pyrus для date обычно строка "YYYY-MM-DD" или объект со строкой внутри
    if value is None:
        return None
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, dict):
        v = value.get("date") or value.get("value") or value.get("text")
        if isinstance(v, str):
            return v[:10]
    return None


def _is_empty_choice(value: Any) -> bool:
    # Пусто, если None, пустая строка или чекбокс unchecked/пустой список
    if value is None:
        return True
    if isinstance(value, str):
        return len(value.strip()) == 0
    if isinstance(value, dict):
        if value.get("checkmark") == "unchecked":
            return True
        if value.get("values") in (None, []):
            return True
    if isinstance(value, list):
        return len(value) == 0
    return False


def _text_equals(value: Any, target: str) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() == target.strip().lower()
    if isinstance(value, dict):
        text = value.get("text") or value.get("value")
        if isinstance(text, str):
            return text.strip().lower() == target.strip().lower()
    return False


def check_rules(fields_meta: Dict[int, Dict[str, Any]], task_fields: List[Dict[str, Any]], target_day: str, run_slot: str) -> List[str]:
    """
    Проверить все правила для target_day.

    run_slot: "today21" или "yesterday12" — влияет только на формулировку 4b
    (логика везде: NEXT_CONTACT_DATE > target_day; пусто — ошибка).
    """
    errors: List[str] = []

    # Имена для сообщений
    n_date1 = _name(fields_meta, DATE_1_ID, "Дата 1 урока")
    n_att1 = _name(fields_meta, ATTENDED_1_ID, "Пришел на занятие?")
    n_date_other = _name(fields_meta, DATE_OTHER_GROUP_ID, "Дата первого урока в мою другую группу")
    n_att_other = _name(fields_meta, ATTENDED_OTHER_GROUP_ID, "Пришел на занятие?")
    n_first = _name(fields_meta, FIRST_LESSON_DATE_ID, "Какого числа придет на первое занятие?")
    n_att_first = _name(fields_meta, ATTENDED_FIRST_ID, "Пришел на 1е занятие?")
    n_group_fit = _name(fields_meta, GROUP_FIT_ID, "Группа подходит?")
    n_date2 = _name(fields_meta, SECOND_LESSON_DATE_ID, "Дата 2-го занятия")
    n_att2 = _name(fields_meta, ATTENDED_SECOND_ID, "Пришел на 2-е занятие?")
    n_exit = _name(fields_meta, EXIT_STATUS_ID, "Статус выхода")
    n_next = _name(fields_meta, NEXT_CONTACT_DATE_ID, "Дата след.контакта")

    # Значения
    v_date1 = _as_date_str(_get_field_value(task_fields, DATE_1_ID))
    v_att1 = _get_field_value(task_fields, ATTENDED_1_ID)

    v_date_other = _as_date_str(_get_field_value(task_fields, DATE_OTHER_GROUP_ID))
    v_att_other = _get_field_value(task_fields, ATTENDED_OTHER_GROUP_ID)

    v_first = _as_date_str(_get_field_value(task_fields, FIRST_LESSON_DATE_ID))
    v_att_first = _get_field_value(task_fields, ATTENDED_FIRST_ID)
    v_group_fit = _get_field_value(task_fields, GROUP_FIT_ID)

    v_date2 = _as_date_str(_get_field_value(task_fields, SECOND_LESSON_DATE_ID))
    v_att2 = _get_field_value(task_fields, ATTENDED_SECOND_ID)

    v_exit = _get_field_value(task_fields, EXIT_STATUS_ID)
    v_next = _as_date_str(_get_field_value(task_fields, NEXT_CONTACT_DATE_ID))

    # Правило 0
    if v_date1 == target_day and _is_empty_choice(v_att1):
        errors.append(f"«{n_date1}» — сегодня; «{n_att1}» не отмечено.")

    # Правило 1
    if v_date_other == target_day and _is_empty_choice(v_att_other):
        errors.append(f"«{n_date_other}» — сегодня; «{n_att_other}» не отмечено.")

    # Правило 2
    if v_first == target_day and _is_empty_choice(v_att_first):
        errors.append(f"«{n_first}» — сегодня; «{n_att_first}» не отмечено.")

    # Правило 3 (применяем только если поле даты заполнено на target_day)
    if v_first == target_day and _text_equals(v_att_first, "ДА") and _is_empty_choice(v_group_fit):
        errors.append(f"«{n_att_first}» = ДА; нужно выбрать вариант в «{n_group_fit}».")

    # Правило 4a
    if v_date2 == target_day and _is_empty_choice(v_att2):
        errors.append(f"«{n_date2}» — сегодня; «{n_att2}» не отмечено.")

    # Правило 4b — если статус = «не знает расписание», то дата след.контакта должна быть > target_day
    if _text_equals(v_exit, "не знает расписание"):
        if v_next is None:
            errors.append(f"«{n_exit}» = «не знает расписание»; заполните «{n_next}» позже, чем {target_day}.")
        elif v_next <= target_day:
            # строго больше target_day
            errors.append(f"«{n_exit}» = «не знает расписание»; «{n_next}» должна быть позже, чем {target_day}.")

    return errors


