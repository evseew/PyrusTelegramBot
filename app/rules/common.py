"""
Общие хелперы для правил форм Pyrus.

Содержит функции для извлечения значений полей, работы с датами,
проверки пустоты выбора и сравнения текстов «Да/Нет».
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


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


