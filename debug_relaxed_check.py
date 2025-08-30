#!/usr/bin/env python3
"""
Отладочный прогон правил с ослабленным фильтром:
- считаем нарушение, если соответствующая дата указана (не равна target_day строго)
- цель: увидеть формат ошибок и примеры сообщений

НЕ используется БД. Вывод в консоль.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

import asyncio
import pytz

from app.pyrus_client import PyrusClient

# Поля
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


def _get_field_value(field_list: List[Dict[str, Any]], field_id: int):
    for f in field_list:
        if f.get("id") == field_id:
            return f.get("value")
    return None


def _as_date_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, dict):
        v = value.get("date") or value.get("value") or value.get("text")
        if isinstance(v, str):
            return v[:10]
    return None


def _is_empty(value: Any) -> bool:
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
        t = value.get("text") or value.get("value")
        if isinstance(t, str):
            return t.strip().lower() == target.strip().lower()
    return False


def relaxed_errors(fields_meta: Dict[int, Dict[str, Any]], task_fields: List[Dict[str, Any]], today_str: str) -> List[str]:
    errs: List[str] = []
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

    v_date1 = _as_date_str(_get_field_value(task_fields, DATE_1_ID))
    v_att1 = _get_field_value(task_fields, ATTENDED_1_ID)
    if v_date1 and _is_empty(v_att1):
        errs.append(f"«{n_date1}» указана; «{n_att1}» не отмечено.")

    v_date_other = _as_date_str(_get_field_value(task_fields, DATE_OTHER_GROUP_ID))
    v_att_other = _get_field_value(task_fields, ATTENDED_OTHER_GROUP_ID)
    if v_date_other and _is_empty(v_att_other):
        errs.append(f"«{n_date_other}» указана; «{n_att_other}» не отмечено.")

    v_first = _as_date_str(_get_field_value(task_fields, FIRST_LESSON_DATE_ID))
    v_att_first = _get_field_value(task_fields, ATTENDED_FIRST_ID)
    v_group_fit = _get_field_value(task_fields, GROUP_FIT_ID)
    if v_first and _is_empty(v_att_first):
        errs.append(f"«{n_first}» указана; «{n_att_first}» не отмечено.")
    if v_first and _text_equals(v_att_first, "ДА") and _is_empty(v_group_fit):
        errs.append(f"«{n_att_first}» = ДА; нужно выбрать вариант в «{n_group_fit}».")

    v_date2 = _as_date_str(_get_field_value(task_fields, SECOND_LESSON_DATE_ID))
    v_att2 = _get_field_value(task_fields, ATTENDED_SECOND_ID)
    if v_date2 and _is_empty(v_att2):
        errs.append(f"«{n_date2}» указана; «{n_att2}» не отмечено.")

    v_exit = _get_field_value(task_fields, EXIT_STATUS_ID)
    v_next = _as_date_str(_get_field_value(task_fields, NEXT_CONTACT_DATE_ID))
    if _text_equals(v_exit, "не знает расписание"):
        if v_next is None:
            errs.append(f"«{n_exit}» = «не знает расписание»; заполните «{n_next}» позже, чем {today_str}.")
        elif v_next <= today_str:
            errs.append(f"«{n_exit}» = «не знает расписание»; «{n_next}» должна быть позже, чем {today_str}.")

    return errs


async def main() -> None:
    tz_name = os.getenv("TZ", "Asia/Yekaterinburg")
    tz = pytz.timezone(tz_name)
    today_str = datetime.now(tz).date().isoformat()
    form_id = int(os.getenv("FORM_ID", "2304918"))

    client = PyrusClient()
    meta = await client.get_form_meta(form_id)
    if not meta:
        print("form_meta: ERROR")
        return
    fields_meta = {f.get("id"): {"name": f.get("name"), "type": f.get("type")} for f in meta.get("fields", [])}
    print(f"FORM: {form_id} — {meta.get('name')}")

    total = 0
    with_errs = 0
    examples = []
    async for task in client.iter_register_tasks(form_id, include_archived=False):
        total += 1
        task_id = task.get("id") or task.get("task_id")
        fields = task.get("fields") or []
        errs = relaxed_errors(fields_meta, fields, today_str)
        if errs:
            with_errs += 1
            if len(examples) < 3:
                examples.append((task_id, errs))

    print(f"Tasks scanned: {total}")
    print(f"Tasks with relaxed violations: {with_errs}")
    for tid, errs in examples:
        print("---")
        print(f"task #{tid}:")
        for e in errs:
            print(f" - {e}")


if __name__ == "__main__":
    asyncio.run(main())


