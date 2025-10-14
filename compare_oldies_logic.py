#!/usr/bin/env python3
"""
Сравнение логики обработки старичков между основным скриптом и тестовым.
Выводит детальную информацию о каждой форме для понимания различий.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict

# Загружаем переменные окружения
load_dotenv()

# Добавляем app в путь для импорта
sys.path.append(str(Path(__file__).parent / "app"))

from pyrus_client import PyrusClient


class OldiesLogicComparator:
    """Сравнивает логику обработки старичков."""
    
    def __init__(self):
        self.client = PyrusClient()
        self.target_branch = "Копейск: Коммунистический, 22"
        
    def _get_field_value(self, field_list: List[Dict[str, Any]], field_id: int) -> Optional[Any]:
        """Ищет значение поля по id."""
        for f in field_list or []:
            if f.get("id") == field_id:
                return f.get("value")
            val = f.get("value")
            if isinstance(val, dict) and isinstance(val.get("fields"), list):
                nested = self._get_field_value(val.get("fields") or [], field_id)
                if nested is not None:
                    return nested
        return None
    
    def _extract_teacher_name(self, task_fields: List[Dict[str, Any]], field_id: int) -> str:
        """Извлекает ФИО преподавателя/студента."""
        value = self._get_field_value(task_fields, field_id)
        
        if isinstance(value, dict):
            first_name = value.get("first_name", "")
            last_name = value.get("last_name", "")
            if isinstance(first_name, str) or isinstance(last_name, str):
                full_name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
                if full_name:
                    return full_name
            
            for key in ("text", "name", "value"):
                name_val = value.get(key)
                if isinstance(name_val, str) and name_val.strip():
                    return name_val.strip()
        
        if isinstance(value, str):
            return value.strip()
        
        return "???"
    
    def _extract_branch_name(self, task_fields: List[Dict[str, Any]], field_id: int) -> str:
        """Извлекает название филиала."""
        value = self._get_field_value(task_fields, field_id)
        
        if isinstance(value, dict):
            values = value.get("values")
            if isinstance(values, list) and len(values) > 0:
                return str(values[0]).strip() if values[0] else "???"
            
            rows = value.get("rows")
            if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], list) and len(rows[0]) > 0:
                return str(rows[0][0]).strip() if rows[0][0] else "???"
            
            for key in ("text", "name", "value"):
                branch_val = value.get(key)
                if isinstance(branch_val, str) and branch_val.strip():
                    return branch_val.strip()
        
        if isinstance(value, str):
            return value.strip()
        
        return "???"
    
    def _get_pe_status(self, task_fields: List[Dict[str, Any]], field_id: int) -> str:
        """Получает статус PE."""
        value = self._get_field_value(task_fields, field_id)
        
        if isinstance(value, dict):
            choice_names = value.get("choice_names")
            if isinstance(choice_names, list) and len(choice_names) > 0:
                return str(choice_names[0])
            
            values = value.get("values")
            if isinstance(values, list) and len(values) > 0:
                return str(values[0])
            
            rows = value.get("rows")
            if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], list) and len(rows[0]) > 0:
                return str(rows[0][0])
            
            for key in ("text", "name", "value"):
                status_val = value.get(key)
                if isinstance(status_val, str) and status_val.strip():
                    return status_val.strip()
        
        if isinstance(value, str):
            return value.strip()
        
        return "???"
    
    def _is_valid_pe_status(self, pe_status: str) -> bool:
        """Проверяет валидность статуса PE."""
        valid_statuses = {"PE Start", "PE Future", "PE 5", "Китайский"}
        return pe_status in valid_statuses
    
    def _is_studying_detailed(self, task_fields: List[Dict[str, Any]], field_id: int) -> Dict[str, Any]:
        """Детальная проверка отметки 'учится' с отладкой."""
        value = self._get_field_value(task_fields, field_id)
        
        result = {
            "raw_value": value,
            "value_type": type(value).__name__,
            "is_studying": False,
            "reason": "Неизвестно"
        }
        
        if isinstance(value, bool):
            result["is_studying"] = value
            result["reason"] = f"Прямое булево значение: {value}"
            return result
        
        if isinstance(value, str):
            is_true = value.lower() in ("true", "да", "yes", "1")
            result["is_studying"] = is_true
            result["reason"] = f"Строка '{value}' → {is_true}"
            return result
        
        if isinstance(value, dict):
            # Проверяем различные поля в объекте
            for key in ("checked", "value", "text"):
                val = value.get(key)
                if isinstance(val, bool):
                    result["is_studying"] = val
                    result["reason"] = f"Поле '{key}' = {val}"
                    return result
                if isinstance(val, str):
                    is_true = val.lower() in ("true", "да", "yes", "1")
                    result["is_studying"] = is_true
                    result["reason"] = f"Поле '{key}' = '{val}' → {is_true}"
                    return result
            
            result["reason"] = f"Объект без подходящих полей: {list(value.keys())}"
            return result
        
        if value is None:
            result["reason"] = "Значение None"
            return result
        
        result["reason"] = f"Неподдерживаемый тип: {type(value)}"
        return result
    
    def _parse_date_value(self, value: Any) -> Optional[datetime]:
        """Парсит значение даты."""
        if value is None:
            return None
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            
            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"]:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        
        if isinstance(value, dict):
            date_str = value.get("date")
            if isinstance(date_str, str):
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    pass
            
            text_val = value.get("text") or value.get("value")
            if isinstance(text_val, str):
                return self._parse_date_value(text_val)
        
        return None
    
    def _is_date_in_august_september_2025(self, date_value: Any) -> bool:
        """Проверяет, попадает ли дата в август-сентябрь 2025."""
        if isinstance(date_value, datetime):
            parsed_date = date_value
        else:
            parsed_date = self._parse_date_value(date_value)
        
        if parsed_date is None:
            return False
        
        start_date = datetime(2025, 8, 1)
        end_date = datetime(2025, 9, 30, 23, 59, 59)
        
        return start_date <= parsed_date <= end_date
    
    def _validate_dates_form_2304918(self, task_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Детальная валидация дат с отладкой."""
        date_field_ids = [26, 31, 56]
        filled_dates = []
        date_info = {}
        
        for field_id in date_field_ids:
            value = self._get_field_value(task_fields, field_id)
            parsed_date = self._parse_date_value(value) if value is not None else None
            
            date_info[f"field_{field_id}"] = {
                "raw_value": value,
                "parsed_date": parsed_date,
                "formatted": parsed_date.strftime("%d.%m.%Y") if parsed_date else "ПУСТО",
                "is_valid": self._is_date_in_august_september_2025(parsed_date) if parsed_date else None
            }
            
            if parsed_date is not None:
                filled_dates.append(parsed_date)
        
        # Логика валидации
        if not filled_dates:
            # Все даты пустые - включаем
            is_valid = True
            reason = "Все даты пустые → ВКЛЮЧАЕМ"
        else:
            # Есть заполненные даты - все должны быть из августа-сентября 2025
            all_valid = all(self._is_date_in_august_september_2025(date) for date in filled_dates)
            is_valid = all_valid
            if all_valid:
                reason = f"Все {len(filled_dates)} заполненных дат из авг-сен 2025 → ВКЛЮЧАЕМ"
            else:
                invalid_dates = [date.strftime("%d.%m.%Y") for date in filled_dates 
                               if not self._is_date_in_august_september_2025(date)]
                reason = f"Есть даты вне авг-сен 2025: {invalid_dates} → ИСКЛЮЧАЕМ"
        
        return {
            "is_valid": is_valid,
            "reason": reason,
            "filled_dates_count": len(filled_dates),
            "date_details": date_info
        }
    
    async def compare_logic(self) -> None:
        """Сравнивает логику обработки старичков."""
        print("=" * 100)
        print(f"🔍 СРАВНЕНИЕ ЛОГИКИ СТАРИЧКОВ: {self.target_branch}")
        print("=" * 100)
        print()
        
        form_id = 2304918
        teacher_field_id = 8  # Поле с преподавателем
        studying_field_id = 64  # Поле "УЧИТСЯ (заполняет СО)"
        branch_field_id = 5  # Поле с филиалом
        status_field_id = 7  # Поле со статусом PE
        student_field_id = 2  # Поле с ФИО студента
        
        print("📥 Загружаю и анализирую формы...\n")
        
        # Статистика
        total_forms = 0
        pe_filtered = 0
        branch_filtered = 0
        date_filtered = 0
        final_count = 0
        studying_count = 0
        
        # Для группировки
        students_forms = defaultdict(list)
        
        # Детальная информация
        detailed_info = []
        
        async for task in self.client.iter_register_tasks(form_id, include_archived=True):
            total_forms += 1
            
            task_fields = task.get("fields", [])
            task_id = task.get("id")
            
            # Шаг 1: PE статус
            pe_status = self._get_pe_status(task_fields, status_field_id)
            pe_valid = self._is_valid_pe_status(pe_status)
            
            if not pe_valid:
                continue
            pe_filtered += 1
            
            # Шаг 2: Филиал
            branch_name = self._extract_branch_name(task_fields, branch_field_id)
            
            if branch_name != self.target_branch:
                continue
            branch_filtered += 1
            
            # Шаг 3: Даты
            date_validation = self._validate_dates_form_2304918(task_fields)
            
            if not date_validation["is_valid"]:
                continue
            date_filtered += 1
            
            # Шаг 4: Извлекаем данные
            teacher_name = self._extract_teacher_name(task_fields, teacher_field_id)
            student_name = self._extract_teacher_name(task_fields, student_field_id)
            studying_info = self._is_studying_detailed(task_fields, studying_field_id)
            
            final_count += 1
            if studying_info["is_studying"]:
                studying_count += 1
            
            # Сохраняем детальную информацию
            form_info = {
                "task_id": task_id,
                "teacher_name": teacher_name,
                "student_name": student_name,
                "pe_status": pe_status,
                "branch_name": branch_name,
                "date_validation": date_validation,
                "studying_info": studying_info,
            }
            
            detailed_info.append(form_info)
            
            # Группируем по клиентам
            student_key = f"{student_name}|{branch_name}"
            students_forms[student_key].append(form_info)
        
        print("📊 СТАТИСТИКА ОСНОВНОЙ ЛОГИКИ (без группировки):")
        print(f"   Всего форм: {total_forms}")
        print(f"   После PE фильтра: {pe_filtered}")
        print(f"   После фильтра филиала: {branch_filtered}")
        print(f"   После фильтра дат: {date_filtered}")
        print(f"   Финальное количество: {final_count}")
        print(f"   Учится: {studying_count}")
        print()
        
        # Анализ группировки
        unique_students = len(students_forms)
        total_forms_grouped = sum(len(forms) for forms in students_forms.values())
        duplicates = total_forms_grouped - unique_students
        
        # Логика "хотя бы один" для учёбы
        studying_grouped = 0
        for student_key, forms in students_forms.items():
            if any(form["studying_info"]["is_studying"] for form in forms):
                studying_grouped += 1
        
        print("📊 СТАТИСТИКА С ГРУППИРОВКОЙ:")
        print(f"   Уникальных студентов: {unique_students}")
        print(f"   Дубликатов: {duplicates}")
        print(f"   Учится (логика 'хотя бы один'): {studying_grouped}")
        print()
        
        # Показываем примеры студентов с отметкой "учится"
        print("🔍 ПРИМЕРЫ СТУДЕНТОВ С ОТМЕТКОЙ 'УЧИТСЯ':")
        studying_examples = [info for info in detailed_info if info["studying_info"]["is_studying"]]
        
        if studying_examples:
            for i, example in enumerate(studying_examples[:5], 1):
                print(f"   {i}. {example['student_name']}")
                print(f"      Преподаватель: {example['teacher_name']}")
                print(f"      Поле 64: {example['studying_info']['reason']}")
                print(f"      Task ID: {example['task_id']}")
                print()
        else:
            print("   ❌ НЕ НАЙДЕНО студентов с отметкой 'учится'")
            print()
            
            # Показываем примеры значений поля 64
            print("🔍 ПРИМЕРЫ ЗНАЧЕНИЙ ПОЛЯ 64 (первые 10):")
            for i, example in enumerate(detailed_info[:10], 1):
                print(f"   {i}. {example['student_name']}")
                print(f"      Поле 64: {example['studying_info']['reason']}")
                print(f"      Raw value: {example['studying_info']['raw_value']}")
                print()


async def main():
    """Главная функция."""
    try:
        comparator = OldiesLogicComparator()
        await comparator.compare_logic()
    except KeyboardInterrupt:
        print("\n❌ Отмена выполнения.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if not os.getenv("PYRUS_LOGIN") or not os.getenv("PYRUS_SECURITY_KEY"):
        print("❌ ОШИБКА: Не установлены переменные окружения")
        sys.exit(1)
    
    asyncio.run(main())
