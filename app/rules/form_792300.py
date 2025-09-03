"""
Правила проверки для формы 792300.

Контракт как у формы 2304918: check_rules(fields_meta, task_fields, target_day, run_slot)
возвращает словарь с ключами "general" и "rule3". Для этой формы все ошибки
относим в "general" и адресуем преподавателю из поля TEACHER_ID_792300.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    _name,
    _get_field_value,
    _as_date_str,
    _is_empty_choice,
    _text_equals,
)


# Поля формы 792300
TEACHER_ID_792300 = 142

DATE_BPZ_ID = 220  # Дата БПЗ
ATTENDED_FIRST_ID = 183  # Пришел на 1ое занятие? (пусто/Да/Нет)
GROUP_FIT_ID = 185  # Группа подходит? (пусто/Да/Нет)

DATE_SECOND_ID = 197  # Дата 2го занятия
ATTENDED_SECOND_ID = 198  # Пришел на 2ое занятие? (пусто/Да/Нет)

NEEDED_GROUP_TEXT_ID = 155  # Какая группа нужна? Напишите подробно (текст)
INVITED_GROUP_TEXT_ID = 242  # В какую группу пригласили? (текст)
INVITED_DATE_ID = 243  # На какую дату пригласили? (в этой форме: пусто/Да/Нет не используется; проверяем непусто)


def check_rules(
    fields_meta: Dict[int, Dict[str, Any]],
    task_fields: List[Dict[str, Any]],
    target_day: str,
    run_slot: str,
) -> Dict[str, List[str]]:
    """
    Проверить правила для формы 792300.

    Гейтинг: ветки правил 1-3 проверяются относительно даты в поле Дата БПЗ (220) == target_day.
    Правило 4 — относительно даты 2-го занятия (197) == target_day.
    """
    errors_general: List[str] = []

    # Имена для сообщений
    n_date_bpz = _name(fields_meta, DATE_BPZ_ID, "Дата БПЗ")
    n_att_first = _name(fields_meta, ATTENDED_FIRST_ID, "Пришел на 1ое занятие?")
    n_group_fit = _name(fields_meta, GROUP_FIT_ID, "Группа подходит?")
    n_date_second = _name(fields_meta, DATE_SECOND_ID, "Дата 2го занятия")
    n_att_second = _name(fields_meta, ATTENDED_SECOND_ID, "Пришел на 2ое занятие?")
    n_needed_group = _name(fields_meta, NEEDED_GROUP_TEXT_ID, "Какая группа нужна? Напишите подробно")
    n_invited_group = _name(fields_meta, INVITED_GROUP_TEXT_ID, "В какую группу пригласили?")
    n_invited_date = _name(fields_meta, INVITED_DATE_ID, "На какую дату пригласили?")

    # Значения
    v_date_bpz = _as_date_str(_get_field_value(task_fields, DATE_BPZ_ID))
    v_att_first = _get_field_value(task_fields, ATTENDED_FIRST_ID)
    v_group_fit = _get_field_value(task_fields, GROUP_FIT_ID)

    v_date_second = _as_date_str(_get_field_value(task_fields, DATE_SECOND_ID))
    v_att_second = _get_field_value(task_fields, ATTENDED_SECOND_ID)

    v_needed_group = _get_field_value(task_fields, NEEDED_GROUP_TEXT_ID)
    v_invited_group = _get_field_value(task_fields, INVITED_GROUP_TEXT_ID)
    v_invited_date_raw = _get_field_value(task_fields, INVITED_DATE_ID)
    v_invited_date = _as_date_str(v_invited_date_raw) or (str(v_invited_date_raw).strip() if isinstance(v_invited_date_raw, str) else None)

    # Правило 1: если Дата БПЗ == target_day и 183 пусто — ошибка
    if v_date_bpz == target_day and _is_empty_choice(v_att_first):
        errors_general.append(f"«{n_date_bpz}» — сегодня; «{n_att_first}» не отмечено.")

    # Правило 2: если 183 == Да и Дата БПЗ == target_day, то 185 и 197 должны быть заполнены
    if v_date_bpz == target_day and _text_equals(v_att_first, "ДА"):
        if _is_empty_choice(v_group_fit):
            errors_general.append(f"«{n_att_first}» = ДА; нужно выбрать вариант в «{n_group_fit}».")
        if v_date_second is None:
            errors_general.append(f"«{n_att_first}» = ДА; заполните «{n_date_second}».")

    # Правило 3: если 183 == Нет и Дата БПЗ == target_day, то 155, 242 — непустой текст; 243 — не пусто (дата)
    if v_date_bpz == target_day and _text_equals(v_att_first, "НЕТ"):
        if not (isinstance(v_needed_group, str) and v_needed_group.strip()):
            errors_general.append(f"«{n_att_first}» = НЕТ; заполните «{n_needed_group}».")
        if not (isinstance(v_invited_group, str) and v_invited_group.strip()):
            errors_general.append(f"«{n_att_first}» = НЕТ; заполните «{n_invited_group}».")
        if v_invited_date is None:
            errors_general.append(f"«{n_att_first}» = НЕТ; заполните «{n_invited_date}».")

    # Правило 4: если Дата 2го занятия == target_day и 198 пусто — ошибка
    if v_date_second == target_day and _is_empty_choice(v_att_second):
        errors_general.append(f"«{n_date_second}» — сегодня; «{n_att_second}» не отмечено.")

    return {"general": errors_general, "rule3": []}


