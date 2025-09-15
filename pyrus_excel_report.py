#!/usr/bin/env python3
"""
Скрипт для создания Excel отчета по данным из Pyrus.

Анализирует две формы:
- 2304918: возврат студентов (поле 8 - преподаватель, поле 64 - учится)
- 792300: конверсия trial (поле 142 - преподаватель, поле 187 - учится)

Создает Excel файл с:
- Основной отчет: сводка по преподавателям
- Детализация: разбивка по формам
- Исходные данные: для проверки расчетов
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Добавляем app в путь для импорта
sys.path.append(str(Path(__file__).parent / "app"))

from pyrus_client import PyrusClient


class TeacherStats:
    """Статистика по преподавателю."""
    
    def __init__(self, name: str):
        self.name = name
        # Форма 2304918 (возврат студентов)
        self.form_2304918_total = 0
        self.form_2304918_studying = 0
        self.form_2304918_data = []  # Исходные данные для проверки
        
        # Форма 792300 (конверсия trial)
        self.form_792300_total = 0
        self.form_792300_studying = 0
        self.form_792300_data = []  # Исходные данные для проверки
    
    @property
    def return_percentage(self) -> float:
        """Процент возврата студентов (форма 2304918)."""
        if self.form_2304918_total == 0:
            return 0.0
        return (self.form_2304918_studying / self.form_2304918_total) * 100
    
    @property
    def conversion_percentage(self) -> float:
        """Процент конверсии trial → студент (форма 792300)."""
        if self.form_792300_total == 0:
            return 0.0
        return (self.form_792300_studying / self.form_792300_total) * 100
    
    @property
    def total_percentage(self) -> float:
        """Суммарный процент двух показателей."""
        return self.return_percentage + self.conversion_percentage


class PyrusDataAnalyzer:
    """Анализатор данных из Pyrus для создания Excel отчета."""
    
    def __init__(self):
        self.client = PyrusClient()
        self.teachers_stats: Dict[str, TeacherStats] = {}
    
    def _get_field_value(self, field_list: List[Dict[str, Any]], field_id: int) -> Optional[Any]:
        """Ищет значение поля по id, рекурсивно обходя вложенные секции."""
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
        """Извлекает ФИО преподавателя из поля справочника."""
        value = self._get_field_value(task_fields, field_id)
        
        if isinstance(value, dict):
            # Поддержка person-объекта: first_name/last_name
            first_name = value.get("first_name", "")
            last_name = value.get("last_name", "")
            if isinstance(first_name, str) or isinstance(last_name, str):
                full_name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
                if full_name:
                    return full_name
            
            # Для справочника сотрудников обычно есть поле text или name
            for key in ("text", "name", "value"):
                name_val = value.get(key)
                if isinstance(name_val, str) and name_val.strip():
                    return name_val.strip()
        
        if isinstance(value, str):
            return value.strip()
        
        return "Неизвестный преподаватель"
    
    def _is_studying(self, task_fields: List[Dict[str, Any]], field_id: int) -> bool:
        """Проверяет, отмечена ли галочка 'учится' в указанном поле."""
        value = self._get_field_value(task_fields, field_id)
        
        if value is None:
            return False
        
        # Булево значение
        if isinstance(value, bool):
            return value
        
        # Строковое значение (checked/unchecked)
        if isinstance(value, str):
            return value.lower() in ("да", "yes", "true", "checked")
        
        # Объект с чекбоксом
        if isinstance(value, dict):
            checkmark = value.get("checkmark")
            if checkmark == "checked":
                return True
        
        return False
    
    async def analyze_form_2304918(self) -> None:
        """Анализ формы 2304918 (возврат студентов)."""
        print("Анализ формы 2304918 (возврат студентов)...")
        
        form_id = 2304918
        teacher_field_id = 8  # Поле с преподавателем
        studying_field_id = 64  # Поле "УЧИТСЯ (заполняет СО)"
        
        task_count = 0
        async for task in self.client.iter_register_tasks(form_id, include_archived=False):
            task_count += 1
            if task_count % 100 == 0:
                print(f"Обработано {task_count} задач формы 2304918...")
            
            task_fields = task.get("fields", [])
            task_id = task.get("id")
            
            # Извлекаем преподавателя
            teacher_name = self._extract_teacher_name(task_fields, teacher_field_id)
            
            # Инициализируем статистику преподавателя если нужно
            if teacher_name not in self.teachers_stats:
                self.teachers_stats[teacher_name] = TeacherStats(teacher_name)
            
            stats = self.teachers_stats[teacher_name]
            
            # Увеличиваем общий счетчик
            stats.form_2304918_total += 1
            
            # Проверяем отметку "учится"
            is_studying = self._is_studying(task_fields, studying_field_id)
            if is_studying:
                stats.form_2304918_studying += 1
            
            # Сохраняем данные для детализации
            stats.form_2304918_data.append({
                "task_id": task_id,
                "teacher": teacher_name,
                "is_studying": is_studying
            })
        
        print(f"Завершен анализ формы 2304918. Обработано {task_count} задач.")
    
    async def analyze_form_792300(self) -> None:
        """Анализ формы 792300 (конверсия trial)."""
        print("Анализ формы 792300 (конверсия trial)...")
        
        form_id = 792300
        teacher_field_id = 142  # Поле с преподавателем
        studying_field_id = 187  # Поле "учится"
        
        task_count = 0
        async for task in self.client.iter_register_tasks(form_id, include_archived=False):
            task_count += 1
            if task_count % 100 == 0:
                print(f"Обработано {task_count} задач формы 792300...")
            
            task_fields = task.get("fields", [])
            task_id = task.get("id")
            
            # Извлекаем преподавателя
            teacher_name = self._extract_teacher_name(task_fields, teacher_field_id)
            
            # Инициализируем статистику преподавателя если нужно
            if teacher_name not in self.teachers_stats:
                self.teachers_stats[teacher_name] = TeacherStats(teacher_name)
            
            stats = self.teachers_stats[teacher_name]
            
            # Увеличиваем общий счетчик
            stats.form_792300_total += 1
            
            # Проверяем отметку "учится"
            is_studying = self._is_studying(task_fields, studying_field_id)
            if is_studying:
                stats.form_792300_studying += 1
            
            # Сохраняем данные для детализации
            stats.form_792300_data.append({
                "task_id": task_id,
                "teacher": teacher_name,
                "is_studying": is_studying
            })
        
        print(f"Завершен анализ формы 792300. Обработано {task_count} задач.")
    
    def create_excel_reports(self, filename: str = "pyrus_teacher_report.xlsx") -> None:
        """Создает один Excel файл с 3 вкладками по категориям преподавателей."""
        print(f"Создание Excel отчета с категориями: {filename}")
        
        # Разделяем преподавателей по категориям
        categories = {
            "6-15 форм": [],
            "16-30 форм": [],
            "31+ форм": []
        }
        
        for teacher_name, stats in self.teachers_stats.items():
            form_count = stats.form_2304918_total
            
            if 6 <= form_count <= 15:
                categories["6-15 форм"].append((teacher_name, stats))
            elif 16 <= form_count <= 30:
                categories["16-30 форм"].append((teacher_name, stats))
            elif form_count >= 31:
                categories["31+ форм"].append((teacher_name, stats))
            # Пропускаем преподавателей с менее чем 6 формами
        
        # Создаем один файл с несколькими листами
        wb = Workbook()
        
        # Удаляем дефолтный лист
        wb.remove(wb.active)
        
        # Создаем вкладку для каждой категории
        for category_name, teachers_list in categories.items():
            if not teachers_list:
                print(f"⚠️ Категория '{category_name}': нет данных")
                continue
            
            print(f"Создание вкладки '{category_name}': {len(teachers_list)} преподавателей")
            self._create_summary_sheet_for_category(wb, teachers_list, category_name)
        
        # Сохраняем файл
        wb.save(filename)
        print(f"✅ Отчет сохранен: {filename}")
        print("Файл содержит вкладки для каждой категории преподавателей!")
    
    def _create_summary_sheet_for_category(self, wb: Workbook, teachers_list: List[Tuple[str, 'TeacherStats']], category_name: str) -> None:
        """Создает лист с отчетом для конкретной категории преподавателей."""
        ws = wb.create_sheet(f"Преподаватели {category_name}")
        
        # Заголовки
        headers = [
            "ФИО преподавателя",
            "2304918: Всего форм",
            "2304918: Учится",
            "2304918: % возврата",
            "792300: Всего форм", 
            "792300: Учится",
            "792300: % конверсии",
            "Итоговый %"
        ]
        
        # Применяем заголовки
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        # Сортируем по итоговому проценту (по убыванию)
        sorted_teachers = sorted(teachers_list, key=lambda x: x[1].total_percentage, reverse=True)
        
        # Данные по преподавателям
        row = 2
        for teacher_name, stats in sorted_teachers:
            ws.cell(row=row, column=1, value=stats.name)
            ws.cell(row=row, column=2, value=stats.form_2304918_total)
            ws.cell(row=row, column=3, value=stats.form_2304918_studying)
            ws.cell(row=row, column=4, value=round(stats.return_percentage, 2))
            ws.cell(row=row, column=5, value=stats.form_792300_total)
            ws.cell(row=row, column=6, value=stats.form_792300_studying)
            ws.cell(row=row, column=7, value=round(stats.conversion_percentage, 2))
            ws.cell(row=row, column=8, value=round(stats.total_percentage, 2))
            row += 1
        
        # Автоширина колонок
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    
    async def run_analysis(self) -> None:
        """Запускает полный анализ данных."""
        print("Начинаем анализ данных из Pyrus...")
        print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Анализируем обе формы
        await self.analyze_form_2304918()
        await self.analyze_form_792300()
        
        # Выводим краткую статистику с разбивкой по категориям
        print("\n=== КРАТКАЯ СТАТИСТИКА ===")
        total_teachers = len(self.teachers_stats)
        print(f"Всего преподавателей: {total_teachers}")
        
        # Статистика по категориям
        categories_count = {
            "6-15 форм": 0,
            "16-30 форм": 0,
            "31+ форм": 0,
            "< 6 форм (исключены)": 0
        }
        
        for stats in self.teachers_stats.values():
            form_count = stats.form_2304918_total
            if 6 <= form_count <= 15:
                categories_count["6-15 форм"] += 1
            elif 16 <= form_count <= 30:
                categories_count["16-30 форм"] += 1
            elif form_count >= 31:
                categories_count["31+ форм"] += 1
            else:
                categories_count["< 6 форм (исключены)"] += 1
        
        print("\nРазбивка по категориям:")
        for category, count in categories_count.items():
            print(f"  {category}: {count} преподавателей")
        
        if total_teachers > 0:
            print("\nТоп-5 преподавателей по итоговому проценту:")
            sorted_teachers = sorted(
                self.teachers_stats.values(),
                key=lambda x: x.total_percentage,
                reverse=True
            )
            for i, stats in enumerate(sorted_teachers[:5], 1):
                print(f"{i}. {stats.name}: {stats.total_percentage:.2f}% "
                      f"(возврат: {stats.return_percentage:.2f}%, "
                      f"конверсия: {stats.conversion_percentage:.2f}%) "
                      f"[{stats.form_2304918_total} форм 2304918]")
        
        # Создаем Excel отчет с категориями по вкладкам
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pyrus_teacher_report_{timestamp}.xlsx"
        self.create_excel_reports(filename)
        
        print(f"\nАнализ завершен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


async def main():
    """Главная функция скрипта."""
    try:
        analyzer = PyrusDataAnalyzer()
        await analyzer.run_analysis()
    except KeyboardInterrupt:
        print("\nОтмена выполнения пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Проверяем переменные окружения
    if not os.getenv("PYRUS_LOGIN") or not os.getenv("PYRUS_SECURITY_KEY"):
        print("ОШИБКА: Не установлены переменные окружения PYRUS_LOGIN и PYRUS_SECURITY_KEY")
        print("Убедитесь, что .env файл настроен корректно.")
        sys.exit(1)
    
    asyncio.run(main())
