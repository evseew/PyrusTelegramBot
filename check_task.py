#!/usr/bin/env python3
"""
Инструмент для диагностики конкретной задачи Pyrus.

Использование:
    python check_task.py <task_id>

Пример:
    python check_task.py 283768656

Анализирует:
1. Проблемы с правилами форм (стандартные нарушения)
2. Проблемы с посещаемостью (не дошёл до 1-го/2-го занятия)
3. Статус регистрации преподавателя в боте
4. Поля задачи и их значения
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Добавляем корень проекта в path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Попытка импорта модулей приложения
try:
    from app.pyrus_client import PyrusClient
    pyrus_client_available = True
except (ImportError, Exception) as e:
    print(f"⚠️ PyrusClient недоступен: {e}")
    pyrus_client_available = False
    PyrusClient = None

try:
    from app.db import db
    db_available = True
except (ImportError, Exception) as e:
    print(f"⚠️ DB недоступен: {e}")
    db_available = False
    db = None

# Импортируем логику проверки правил для разных форм
rules_2304918_available = False
rules_792300_available = False
check_rules_2304918 = None
check_rules_792300 = None
_get_field_value = None

try:
    from app.rules.form_2304918 import check_rules as check_rules_2304918, _get_field_value
    rules_2304918_available = True
except (ImportError, Exception) as e:
    print(f"⚠️ Правила для формы 2304918 недоступны: {e}")

try:
    from app.rules.form_792300 import check_rules as check_rules_792300
    rules_792300_available = True
    if not _get_field_value:
        try:
            from app.rules.form_792300 import _get_field_value
        except ImportError:
            pass
except (ImportError, Exception) as e:
    print(f"⚠️ Правила для формы 792300 недоступны: {e}")

# Константы для контроля посещаемости (из managers_problems_report.py)
ATTENDANCE_CONTROL_FIELDS = {
    2304918: {
        "check_fields": [27, 32, 50, 57],  # Проверяем "Нет" в любом из этих полей
        "completion_field": 64,  # УЧИТСЯ (заполняет СО) - убираем из контроля когда галочка стоит
        "exclusion_field": 25,  # Статус выхода - исключаем если "Не выйдет" или "Выходит на ИЗ"
        "exclusion_values": ["не выйдет", "выходит на из"]
    },
    792300: {
        "check_fields": [183, 198],  # Пришел на 1ое/2ое занятие? - проверяем "Нет" 
        "completion_field": 187  # УЧИТСЯ - убираем из контроля когда галочка стоит
    }
}

FIELD_NAMES_792300 = {
    183: "Пришел на 1-е занятие?",
    198: "Пришел на 2-е занятие?", 
    187: "УЧИТСЯ"
}

FIELD_NAMES_2304918 = {
    27: "Прошел ли 1-е занятие?",
    32: "Прошел ли 2-е занятие?",
    50: "Прошел ли 3-е занятие?",
    57: "Прошел ли 4-е занятие?",
    64: "УЧИТСЯ (заполняет СО)",
    25: "Статус выхода"
}


def _get_field_value_fallback(task_fields: List[Dict[str, Any]], field_id: int) -> Any:
    """Резервная функция для получения значения поля."""
    for field in task_fields:
        if field.get("id") == field_id:
            value = field.get("value", {})
            if isinstance(value, dict):
                # Для чекбоксов
                if "checkmark" in value:
                    return value
                # Для текстовых полей
                return value.get("text") or value.get("value") or value.get("name", "")
            return value
    return None


def check_attendance_problems(task_fields: List[Dict[str, Any]], form_id: int) -> Tuple[bool, str, List[str]]:
    """
    Проверяет проблемы с посещаемостью.
    
    Returns:
        tuple[bool, str, List[str]]: (есть_проблема, детали_занятия, список_проблем)
    """
    control_config = ATTENDANCE_CONTROL_FIELDS.get(form_id)
    if not control_config:
        return False, "", []
    
    field_names = FIELD_NAMES_792300 if form_id == 792300 else FIELD_NAMES_2304918
    
    # Проверяем поле завершения - если там "Да" или галочка, то контроль не нужен
    completion_field_id = control_config["completion_field"]
    try:
        completion_value = _get_field_value(task_fields, completion_field_id)
    except NameError:
        completion_value = _get_field_value_fallback(task_fields, completion_field_id)
    
    # Проверяем галочку "УЧИТСЯ" - если стоит, то контроль не нужен
    if isinstance(completion_value, dict):
        checkmark = completion_value.get("checkmark")
        if checkmark == "checked":
            return False, "Галочка 'УЧИТСЯ' стоит - контроль не нужен", []
        text_value = completion_value.get("text", "").lower()
        if text_value in ["да", "yes"]:
            return False, "Поле 'УЧИТСЯ' = 'Да' - контроль не нужен", []
    elif isinstance(completion_value, str):
        if completion_value.lower() in ["да", "yes", "checked"]:
            return False, "Поле 'УЧИТСЯ' = 'Да' - контроль не нужен", []
    
    # Проверяем поле исключения (только для формы 2304918)
    exclusion_field_id = control_config.get("exclusion_field")
    if exclusion_field_id:
        try:
            exclusion_value = _get_field_value(task_fields, exclusion_field_id)
        except NameError:
            exclusion_value = _get_field_value_fallback(task_fields, exclusion_field_id)
            
        if isinstance(exclusion_value, str):
            exclusion_text = exclusion_value.lower()
            exclusion_values = control_config.get("exclusion_values", [])
            if any(excl_val in exclusion_text for excl_val in exclusion_values):
                return False, f"Статус исключения: '{exclusion_value}' - контроль не нужен", []
    
    # Проверяем поля посещаемости
    check_fields = control_config["check_fields"]
    problems = []
    lesson_details = []
    
    for field_id in check_fields:
        try:
            field_value = _get_field_value(task_fields, field_id)
        except NameError:
            field_value = _get_field_value_fallback(task_fields, field_id)
            
        field_name = field_names.get(field_id, f"Поле {field_id}")
        
        # Проверяем на значение "Нет" 
        if isinstance(field_value, str) and field_value.lower() in ["нет", "no"]:
            problems.append(f"{field_name}: {field_value}")
            if "1-е занятие" in field_name:
                lesson_details.append("1-е занятие")
            elif "2-е занятие" in field_name:
                lesson_details.append("2-е занятие")
            elif "3-е занятие" in field_name:
                lesson_details.append("3-е занятие")
            elif "4-е занятие" in field_name:
                lesson_details.append("4-е занятие")
        elif isinstance(field_value, dict):
            text_val = field_value.get("text", "").lower()
            if text_val in ["нет", "no"]:
                problems.append(f"{field_name}: {text_val}")
                if "1-е занятие" in field_name:
                    lesson_details.append("1-е занятие")
                elif "2-е занятие" in field_name:
                    lesson_details.append("2-е занятие")
    
    has_problems = bool(problems)
    lesson_summary = ", ".join(lesson_details) if lesson_details else ""
    
    return has_problems, lesson_summary, problems


async def analyze_task(task_id: int) -> Dict[str, Any]:
    """Анализирует конкретную задачу Pyrus."""
    if not pyrus_client_available:
        return {"error": "PyrusClient недоступен - невозможно получить данные задачи"}
    
    client = PyrusClient()
    
    try:
        # Получаем данные задачи
        task_data = await client.get_task(task_id)
        if not task_data:
            return {"error": f"Задача {task_id} не найдена"}
        
        # Определяем ID формы
        form_id = task_data.get("form_id")
        if not form_id:
            return {"error": f"Не удалось определить ID формы для задачи {task_id}"}
        
        # Получаем метаданные формы
        form_meta = await client.get_form_meta(form_id)
        form_name = form_meta.get("name", f"Форма {form_id}") if form_meta else f"Форма {form_id}"
        
        task_fields = task_data.get("fields", [])
        task_title = task_data.get("subject") or task_data.get("text") or f"Задача #{task_id}"
        
        result = {
            "task_id": task_id,
            "form_id": form_id,
            "form_name": form_name,
            "task_title": task_title,
            "pyrus_link": f"https://pyrus.com/t#id{task_id}",
            "fields_count": len(task_fields),
            "analysis": {}
        }
        
        # Анализ 1: Проблемы с правилами форм
        rules_errors = []
        if form_id == 2304918 and rules_2304918_available:
            try:
                from datetime import datetime, timedelta
                import pytz
                
                # Вчерашний день для проверки
                tz = pytz.timezone("Asia/Yekaterinburg")
                yesterday = (datetime.now(tz) - timedelta(days=1)).strftime("%Y-%m-%d")
                
                errors_map = check_rules_2304918(form_meta.get("fields", []), task_fields, yesterday, "yesterday12")
                general_errors = errors_map.get("general", [])
                rule3_errors = errors_map.get("rule3", [])
                rules_errors = general_errors + rule3_errors
                
            except Exception as e:
                rules_errors = [f"Ошибка при проверке правил: {e}"]
        
        elif form_id == 792300 and rules_792300_available:
            try:
                from datetime import datetime, timedelta
                import pytz
                
                tz = pytz.timezone("Asia/Yekaterinburg")
                yesterday = (datetime.now(tz) - timedelta(days=1)).strftime("%Y-%m-%d")
                
                errors_map = check_rules_792300(form_meta.get("fields", []), task_fields, yesterday, "yesterday12")
                general_errors = errors_map.get("general", [])
                rule3_errors = errors_map.get("rule3", [])
                rules_errors = general_errors + rule3_errors
                
            except Exception as e:
                rules_errors = [f"Ошибка при проверке правил: {e}"]
        
        result["analysis"]["rules_errors"] = rules_errors
        
        # Анализ 2: Проблемы с посещаемостью
        has_attendance_problem, lesson_detail, attendance_problems = check_attendance_problems(task_fields, form_id)
        
        result["analysis"]["attendance"] = {
            "has_problem": has_attendance_problem,
            "lesson_detail": lesson_detail,
            "problems": attendance_problems
        }
        
        # Анализ 3: Важные поля
        important_fields = {}
        field_names = FIELD_NAMES_792300 if form_id == 792300 else FIELD_NAMES_2304918
        
        for field_id, field_name in field_names.items():
            try:
                value = _get_field_value(task_fields, field_id)
            except NameError:
                value = _get_field_value_fallback(task_fields, field_id)
            important_fields[f"{field_name} (ID:{field_id})"] = value
        
        result["analysis"]["important_fields"] = important_fields
        
        # Анализ 4: Все поля для отладки
        all_fields = {}
        for field in task_fields:
            field_id = field.get("id")
            field_name = field.get("name", f"Поле {field_id}")
            field_value = field.get("value", {})
            all_fields[f"{field_name} (ID:{field_id})"] = field_value
        
        result["analysis"]["all_fields"] = all_fields
        
        return result
        
    except Exception as e:
        return {"error": f"Ошибка при анализе задачи: {e}"}


def print_analysis_results(result: Dict[str, Any]) -> None:
    """Выводит результаты анализа в читаемом виде."""
    if "error" in result:
        print(f"❌ ОШИБКА: {result['error']}")
        return
    
    print("=" * 80)
    print(f"📋 АНАЛИЗ ЗАДАЧИ PYRUS")
    print("=" * 80)
    print(f"🆔 ID задачи: {result['task_id']}")
    print(f"📝 Название: {result['task_title']}")
    print(f"📄 Форма: {result['form_name']} (ID: {result['form_id']})")
    print(f"🔗 Ссылка: {result['pyrus_link']}")
    print(f"📊 Полей в задаче: {result['fields_count']}")
    print()
    
    analysis = result["analysis"]
    
    # Результаты проверки правил
    print("🔍 ПРОВЕРКА ПРАВИЛ ФОРМ:")
    rules_errors = analysis.get("rules_errors", [])
    if rules_errors:
        print(f"   ❌ Найдено {len(rules_errors)} нарушений:")
        for i, error in enumerate(rules_errors, 1):
            print(f"      {i}. {error}")
    else:
        print("   ✅ Нарушений правил не найдено")
    print()
    
    # Результаты проверки посещаемости
    print("👥 ПРОВЕРКА ПОСЕЩАЕМОСТИ:")
    attendance = analysis.get("attendance", {})
    if attendance.get("has_problem"):
        print(f"   ❌ Проблема с посещаемостью: {attendance.get('lesson_detail')}")
        for problem in attendance.get("problems", []):
            print(f"      • {problem}")
    else:
        print("   ✅ Проблем с посещаемостью не найдено")
    print()
    
    # Важные поля
    print("📋 ВАЖНЫЕ ПОЛЯ:")
    important_fields = analysis.get("important_fields", {})
    for field_name, value in important_fields.items():
        print(f"   {field_name}: {value}")
    print()
    
    # Общее заключение
    total_problems = len(rules_errors) + (1 if attendance.get("has_problem") else 0)
    print("📊 ЗАКЛЮЧЕНИЕ:")
    if total_problems == 0:
        print("   ✅ Проблем не обнаружено - задача попала в отчёт ошибочно")
    else:
        print(f"   ❌ Обнаружено проблем: {total_problems}")
        if rules_errors:
            print(f"      • Нарушения правил: {len(rules_errors)}")
        if attendance.get("has_problem"):
            print(f"      • Проблемы с посещаемостью: {attendance.get('lesson_detail')}")
    print()


async def main():
    """Главная функция."""
    if len(sys.argv) != 2:
        print("Использование: python check_task.py <task_id>")
        print("Пример: python check_task.py 283768656")
        sys.exit(1)
    
    try:
        task_id = int(sys.argv[1])
    except ValueError:
        print("❌ Ошибка: ID задачи должен быть числом")
        sys.exit(1)
    
    print(f"🔍 Анализируем задачу {task_id}...")
    print()
    
    result = await analyze_task(task_id)
    print_analysis_results(result)
    
    # Дополнительная отладочная информация
    if "--debug" in sys.argv:
        print("🐛 ОТЛАДОЧНАЯ ИНФОРМАЦИЯ:")
        print("   Все поля задачи:")
        all_fields = result.get("analysis", {}).get("all_fields", {})
        for field_name, value in all_fields.items():
            print(f"      {field_name}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
