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
# Преподаватель для уведомления по правилу 3
TEACHER_RULE3_ID = 49
DATE_1_ID = 26
ATTENDED_1_ID = 27
DATE_OTHER_GROUP_ID = 31
ATTENDED_OTHER_GROUP_ID = 32
# Поле "Клиента забрали" - если стоит галочка, уведомления не отправляются
CLIENT_TAKEN_ID = 37
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
    """Ищет значение поля по id, рекурсивно обходя вложенные секции/группы.

    Pyrus для секций/групп кладёт в value словарь с ключом "fields": [...].
    """
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
    # Пусто, если None, пустая строка, булево False или чекбокс unchecked/пустой список
    if value is None:
        return True
    if isinstance(value, str):
        return len(value.strip()) == 0
    if isinstance(value, bool):
        # Булево значение — это осознанный ответ (да/нет), не считаем пустым
        return False
    if isinstance(value, dict):
        # Если есть явный чекмаркер — это ответ, даже если unchecked (это «нет»)
        if value.get("checkmark") in ("checked", "unchecked"):
            return False
        
        # ИСПРАВЛЕНО: Сначала проверяем choice_names
        choice_names = value.get("choice_names")
        if isinstance(choice_names, list):
            return len(choice_names) == 0
        
        # Проверяем text/value/name
        text_val = value.get("text") or value.get("value") or value.get("name")
        if isinstance(text_val, str):
            return len(text_val.strip()) == 0
        
        # Проверяем values только если это единственное содержимое
        if value.get("values") in (None, []) and len(value) <= 1:
            return True
            
    if isinstance(value, list):
        return len(value) == 0
    return False


def _text_equals(value: Any, target: str) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() == target.strip().lower()
    if isinstance(value, bool):
        # Нормализуем булевы в текст «да/нет» для сравнения
        normalized = "да" if value else "нет"
        return normalized == target.strip().lower()
    if isinstance(value, dict):
        # Поддержка чекбокса в формате checkmark
        if "checkmark" in value:
            ck = str(value.get("checkmark") or "").strip().lower()
            as_text = "да" if ck == "checked" else "нет" if ck == "unchecked" else ""
            if as_text:
                return as_text == target.strip().lower()
        # Pyrus для choice/multiple_choice часто присылает choice_names
        text = value.get("text") or value.get("value") or value.get("name")
        if isinstance(text, str):
            return text.strip().lower() == target.strip().lower()
        choice_names = value.get("choice_names")
        if isinstance(choice_names, list):
            t = target.strip().lower()
            return any(isinstance(c, str) and c.strip().lower() == t for c in choice_names)
    return False


def _text_in(value: Any, options: List[str]) -> bool:
    """Проверка: совпадает ли текстовое значение с одним из вариантов (без учёта регистра).

    Учитываем, что для multiple_choice Pyrus кладёт список choice_names.
    """
    for opt in options:
        if _text_equals(value, opt):
            return True
    return False


def _value_to_text(value: Any) -> str:
    """Человекочитаемое представление значения для вставки в сообщения."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, dict):
        if "checkmark" in value:
            ck = str(value.get("checkmark") or "").strip().lower()
            return "да" if ck == "checked" else "нет" if ck == "unchecked" else ""
        # Предпочтительно вывести первый choice_name, иначе text/value/name
        choice_names = value.get("choice_names")
        if isinstance(choice_names, list) and choice_names:
            first = choice_names[0]
            if isinstance(first, str):
                return first
        for k in ("text", "value", "name"):
            v = value.get(k)
            if isinstance(v, str):
                return v
    return str(value)


def is_new_teacher_field_filled(task_fields: List[Dict[str, Any]]) -> bool:
    """Проверяет, заполнено ли поле 49 (Новый преподаватель).
    
    Возвращает True, если поле заполнено (не пустое).
    """
    value = _get_field_value(task_fields, TEACHER_RULE3_ID)
    return not _is_empty_choice(value)


def check_rules(fields_meta: Dict[int, Dict[str, Any]], task_fields: List[Dict[str, Any]], target_day: str, run_slot: str) -> Dict[str, List[str]]:
    """
    Проверить все правила для target_day.

    run_slot: "today21" или "yesterday12" — влияет только на формулировку 4b
    (логика везде: NEXT_CONTACT_DATE > target_day; пусто — ошибка).
    """
    errors_general: List[str] = []
    errors_rule3: List[str] = []

    # Проверяем поле "Клиента забрали" (ID=37) - если галочка стоит, не отправляем уведомления
    v_client_taken = _get_field_value(task_fields, CLIENT_TAKEN_ID)
    if v_client_taken is not None:
        # Проверяем, стоит ли галочка (значение True, "checked", "да" и т.п.)
        is_checked = False
        if isinstance(v_client_taken, bool) and v_client_taken:
            is_checked = True
        elif isinstance(v_client_taken, dict):
            checkmark = v_client_taken.get("checkmark")
            if checkmark == "checked":
                is_checked = True
        elif isinstance(v_client_taken, str) and v_client_taken.lower() in ("да", "yes", "true"):
            is_checked = True
        
        # Если клиента забрали, возвращаем пустые ошибки
        if is_checked:
            return {"general": [], "rule3": []}

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
    # Применяем связку (26/27) только если статус НЕ в списке исключений
    # (для «МОЮ другую группу» используется пара 31/32 — см. Правило 1)
    # (для «Подобрать другую группу» используется пара 47/50 — см. Правило 5)
    excluded_statuses = ["Выходит в МОЮ другую группу", "Подобрать другую группу"]
    if (
        v_date1 == target_day
        and _is_empty_choice(v_att1)
        and not _text_in(v_exit, excluded_statuses)
    ):
        errors_general.append(f"«{n_date1}» — сегодня; «{n_att1}» не отмечено.")

    # Правило 1
    if v_date_other == target_day and _is_empty_choice(v_att_other):
        errors_general.append(f"«{n_date_other}» — сегодня; «{n_att_other}» не отмечено.")

    # Правило 2
    if v_first == target_day and _is_empty_choice(v_att_first):
        errors_general.append(f"«{n_first}» — сегодня; «{n_att_first}» не отмечено.")

    # Правило 3 (применяем только если поле даты заполнено на target_day)
    if v_first == target_day and _text_equals(v_att_first, "ДА") and _is_empty_choice(v_group_fit):
        errors_rule3.append(f"«{n_att_first}» = ДА; нужно выбрать вариант в «{n_group_fit}».")

    # Правило 4a
    if v_date2 == target_day and _is_empty_choice(v_att2):
        errors_general.append(f"«{n_date2}» — сегодня; «{n_att2}» не отмечено.")

    # Правило 4b — если статус проблемный, то дата след.контакта должна быть > target_day
    # Добавляем статус «Не вышел на связь :(» помимо «не знает расписание»
    problem_statuses = ["не знает расписание", "не вышел на связь :("]
    if _text_in(v_exit, problem_statuses):
        exit_label = _value_to_text(v_exit) or "проблемный статус"
        if v_next is None:
            errors_general.append(f"«{n_exit}» = «{exit_label}»; заполните «{n_next}» позже, чем {target_day}.")
        elif v_next <= target_day:
            # строго больше target_day
            errors_general.append(f"«{n_exit}» = «{exit_label}»; «{n_next}» должна быть позже, чем {target_day}.")

    # Правило 5 — для статуса "Подобрать другую группу": проверяем поля 47/50
    if _text_equals(v_exit, "Подобрать другую группу") and v_first == target_day and _is_empty_choice(v_att_first):
        errors_general.append(f"«{n_exit}» = «Подобрать другую группу»; «{n_first}» — сегодня; «{n_att_first}» не отмечено.")

    return {"general": errors_general, "rule3": errors_rule3}


