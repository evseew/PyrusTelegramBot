#!/usr/bin/env python3
"""
Диагностический скрипт для анализа расхождения между отчетом и данными Pyrus.

Исследует причины расхождения между:
- Отчет: 147 форм ЧТЗ
- Pyrus: 160 форм ЧТЗ

Возможные причины:
1. Фильтрация по статусу PE (только PE Start, PE Future, PE 5)
2. Исключения преподавателей
3. Исключенные/объединенные филиалы
4. Фильтрация по дате (нет в текущем коде)
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from collections import defaultdict, Counter

import pandas as pd
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Добавляем app в путь для импорта
sys.path.append(str(Path(__file__).parent / "app"))

from pyrus_client import PyrusClient


class DiscrepancyAnalyzer:
    """Анализатор расхождений между отчетом и данными Pyrus."""
    
    def __init__(self):
        self.client = PyrusClient()
        self.excluded_teachers = self._load_exclusions()
        
        # Статистика
        self.total_tasks = 0
        self.filtered_by_status = 0
        self.excluded_by_teacher = 0
        self.excluded_by_branch = 0
        self.final_count = 0
        
        # Детализация по филиалам
        self.raw_branches = Counter()  # Исходные названия филиалов
        self.normalized_branches = Counter()  # После нормализации
        self.excluded_branches = []  # Исключенные филиалы
        
        # Статусы PE
        self.pe_statuses = Counter()
        
        # Преподаватели
        self.teacher_names = Counter()
        self.excluded_teacher_names = []
    
    def _load_exclusions(self) -> Dict[str, Set[str]]:
        """Загружает списки исключений преподавателей из JSON файла."""
        exclusions_file = Path(__file__).parent / "teacher_exclusions.json"
        
        try:
            with open(exclusions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'oldies': set(data.get('oldies', [])),
                    'trial': set(data.get('trial', []))
                }
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ Не удалось загрузить исключения из {exclusions_file}: {e}")
            return {'oldies': set(), 'trial': set()}
    
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
    
    def _extract_branch_name(self, task_fields: List[Dict[str, Any]], field_id: int) -> tuple[str, str]:
        """Извлекает название филиала из поля справочника.
        
        Returns:
            tuple: (raw_name, normalized_name)
        """
        value = self._get_field_value(task_fields, field_id)
        raw_name = "Неизвестный филиал"
        
        if isinstance(value, dict):
            # Проверяем массив values - основной способ для справочника филиалов
            values = value.get("values")
            if isinstance(values, list) and len(values) > 0:
                branch_name = values[0]  # Берем первое значение
                if isinstance(branch_name, str) and branch_name.strip():
                    raw_name = branch_name.strip()
            
            # Проверяем rows если values не найден  
            if raw_name == "Неизвестный филиал":
                rows = value.get("rows")
                if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], list) and len(rows[0]) > 0:
                    branch_name = rows[0][0]  # Берем первую ячейку первой строки
                    if isinstance(branch_name, str) and branch_name.strip():
                        raw_name = branch_name.strip()
            
            # Для обычных справочников обычно есть поле text или name
            if raw_name == "Неизвестный филиал":
                for key in ("text", "name", "value"):
                    branch_val = value.get(key)
                    if isinstance(branch_val, str) and branch_val.strip():
                        raw_name = branch_val.strip()
                        break
        
        if isinstance(value, str):
            raw_name = value.strip()
        
        # Нормализация (из pyrus_excel_report.py)
        normalized_name = self._normalize_branch_name(raw_name)
        
        return raw_name, normalized_name
    
    def _normalize_branch_name(self, branch_name: str) -> Optional[str]:
        """Нормализует название филиала для объединения данных."""
        if not branch_name or branch_name == "Неизвестный филиал":
            return None
            
        branch_name_lower = branch_name.lower().strip()
        
        # Исключаем филиалы из отчета
        if "макеева" in branch_name_lower and "15" in branch_name_lower:
            return None  # Исключаем из отчета
        if "коммуны" in branch_name_lower and "106/1" in branch_name_lower:
            return None  # Исключаем из отчета
        
        # Объединяем филиалы Копейска под единым названием
        if "коммунистический" in branch_name_lower and "22" in branch_name_lower:
            return "Копейск"
        if "славы" in branch_name_lower and "30" in branch_name_lower:
            return "Копейск"
        
        # Возвращаем оригинальное название с заглавной буквы
        return branch_name.title()
    
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
    
    def _is_teacher_excluded(self, teacher_name: str, form_type: str) -> bool:
        """Проверяет, исключен ли преподаватель из указанной формы."""
        excluded_set = self.excluded_teachers.get(form_type, set())
        
        # Проверяем точное совпадение
        if teacher_name in excluded_set:
            return True
        
        # Проверяем частичное совпадение (фамилия входит в имя преподавателя)
        for excluded_name in excluded_set:
            if excluded_name.lower() in teacher_name.lower():
                return True
        
        return False
    
    def _extract_pe_status(self, task_fields: List[Dict[str, Any]], field_id: int) -> str:
        """Извлекает статус PE из поля."""
        value = self._get_field_value(task_fields, field_id)
        
        if isinstance(value, dict):
            # Проверяем choice_names для справочника выбора
            choice_names = value.get("choice_names")
            if isinstance(choice_names, list) and len(choice_names) > 0:
                return choice_names[0]
            
            # Проверяем массив values для справочника
            values = value.get("values")
            if isinstance(values, list) and len(values) > 0:
                return values[0]
            
            # Проверяем rows если values не найден  
            rows = value.get("rows")
            if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], list) and len(rows[0]) > 0:
                return rows[0][0]
            
            # Для обычных справочников проверяем text, name, value
            for key in ("text", "name", "value"):
                status_val = value.get(key)
                if isinstance(status_val, str) and status_val.strip():
                    return status_val.strip()
        
        if isinstance(value, str):
            return value.strip()
        
        return "Неизвестный статус"
    
    def _is_valid_pe_status(self, pe_status: str) -> bool:
        """Проверяет, соответствует ли статус PE одному из допустимых."""
        valid_statuses = {"PE Start", "PE Future", "PE 5"}
        return pe_status in valid_statuses
    
    async def analyze_form_792300(self) -> None:
        """Анализ формы 792300 с детализацией причин исключения."""
        print("🔍 Анализ формы 792300 (конверсия trial)...")
        
        form_id = 792300
        teacher_field_id = 142  # Поле с преподавателем
        branch_field_id = 226  # Поле с филиалом
        status_field_id = 228  # Поле со статусом PE
        
        # Фильтр по филиалам ЧТЗ (различные варианты написания)
        chtz_keywords = ["чтз", "чит", "тракторный", "трактор"]
        
        # Списки для детального анализа исключенных форм
        self.excluded_details = {
            'pe_status': [],  # [(task_id, pe_status, teacher, branch)]
            'teacher': [],    # [(task_id, teacher, branch)]
            'branch': [],     # [(task_id, raw_branch, teacher)]
            'included': []    # [(task_id, teacher, branch, pe_status)]
        }
        
        async for task in self.client.iter_register_tasks(form_id, include_archived=False):
            self.total_tasks += 1
            
            if self.total_tasks % 100 == 0:
                print(f"Обработано {self.total_tasks} задач...")
            
            task_fields = task.get("fields", [])
            task_id = task.get("id")
            
            # Извлекаем данные
            raw_branch, normalized_branch = self._extract_branch_name(task_fields, branch_field_id)
            teacher_name = self._extract_teacher_name(task_fields, teacher_field_id)
            pe_status = self._extract_pe_status(task_fields, status_field_id)
            
            # Фильтруем только ЧТЗ
            is_chtz = any(keyword in raw_branch.lower() for keyword in chtz_keywords)
            if not is_chtz:
                continue
            
            # Статистика
            self.raw_branches[raw_branch] += 1
            self.pe_statuses[pe_status] += 1
            self.teacher_names[teacher_name] += 1
            
            # Проверяем статус PE
            if not self._is_valid_pe_status(pe_status):
                self.filtered_by_status += 1
                self.excluded_details['pe_status'].append((task_id, pe_status, teacher_name, raw_branch))
                continue
            
            # Проверяем исключения преподавателей
            if self._is_teacher_excluded(teacher_name, 'trial'):
                self.excluded_by_teacher += 1
                self.excluded_teacher_names.append(teacher_name)
                self.excluded_details['teacher'].append((task_id, teacher_name, raw_branch))
                continue
            
            # Проверяем нормализацию филиала
            if normalized_branch is None:
                self.excluded_by_branch += 1
                self.excluded_branches.append(raw_branch)
                self.excluded_details['branch'].append((task_id, raw_branch, teacher_name))
                continue
                
            self.normalized_branches[normalized_branch] += 1
            self.excluded_details['included'].append((task_id, teacher_name, normalized_branch, pe_status))
            self.final_count += 1
        
        print(f"✅ Анализ завершен. Обработано {self.total_tasks} задач формы 792300")
    
    async def analyze_form_2304918(self) -> None:
        """Анализ формы 2304918 с детализацией причин исключения."""
        print("🔍 Анализ формы 2304918 (возврат студентов)...")
        
        form_id = 2304918
        teacher_field_id = 8  # Поле с преподавателем
        branch_field_id = 5  # Поле с филиалом
        status_field_id = 7  # Поле со статусом PE
        
        # Фильтр по филиалам ЧТЗ (различные варианты написания)
        chtz_keywords = ["чтз", "чит", "тракторный", "трактор"]
        
        # Сбрасываем счетчики для второй формы
        self.form_2304918_stats = {
            'total_tasks': 0,
            'chtz_tasks': 0,
            'filtered_by_status': 0,
            'excluded_by_teacher': 0,
            'excluded_by_branch': 0,
            'final_count': 0,
            'excluded_details': {
                'pe_status': [],
                'teacher': [],
                'branch': [],
                'included': []
            }
        }
        
        async for task in self.client.iter_register_tasks(form_id, include_archived=False):
            self.form_2304918_stats['total_tasks'] += 1
            
            if self.form_2304918_stats['total_tasks'] % 100 == 0:
                print(f"Обработано {self.form_2304918_stats['total_tasks']} задач формы 2304918...")
            
            task_fields = task.get("fields", [])
            task_id = task.get("id")
            
            # Извлекаем данные
            raw_branch, normalized_branch = self._extract_branch_name(task_fields, branch_field_id)
            teacher_name = self._extract_teacher_name(task_fields, teacher_field_id)
            pe_status = self._extract_pe_status(task_fields, status_field_id)
            
            # Фильтруем только ЧТЗ
            is_chtz = any(keyword in raw_branch.lower() for keyword in chtz_keywords)
            if not is_chtz:
                continue
            
            self.form_2304918_stats['chtz_tasks'] += 1
            
            # Проверяем статус PE
            if not self._is_valid_pe_status(pe_status):
                self.form_2304918_stats['filtered_by_status'] += 1
                self.form_2304918_stats['excluded_details']['pe_status'].append((task_id, pe_status, teacher_name, raw_branch))
                continue
            
            # Проверяем исключения преподавателей для oldies
            if self._is_teacher_excluded(teacher_name, 'oldies'):
                self.form_2304918_stats['excluded_by_teacher'] += 1
                self.form_2304918_stats['excluded_details']['teacher'].append((task_id, teacher_name, raw_branch))
                continue
            
            # Проверяем нормализацию филиала
            if normalized_branch is None:
                self.form_2304918_stats['excluded_by_branch'] += 1
                self.form_2304918_stats['excluded_details']['branch'].append((task_id, raw_branch, teacher_name))
                continue
                
            self.form_2304918_stats['excluded_details']['included'].append((task_id, teacher_name, normalized_branch, pe_status))
            self.form_2304918_stats['final_count'] += 1
        
        print(f"✅ Анализ формы 2304918 завершен. ЧТЗ задач: {self.form_2304918_stats['chtz_tasks']}")
    
    def print_report(self) -> None:
        """Выводит детальный отчет по анализу."""
        print("\n" + "="*80)
        print("📊 ОТЧЕТ ПО АНАЛИЗУ РАСХОЖДЕНИЙ")
        print("="*80)
        
        # Общая статистика по ЧТЗ для формы 792300
        chtz_total = sum(self.raw_branches.values())
        print(f"\n🏢 СТАТИСТИКА ПО ЧТЗ (форма 792300 - конверсия trial):")
        print(f"Всего задач ЧТЗ в Pyrus: {chtz_total}")
        print(f"Расхождение с отчетом: {chtz_total - 147} (если ожидается 147)")
        
        # Детализация фильтрации для 792300
        print(f"\n🔍 ДЕТАЛИЗАЦИЯ ФИЛЬТРАЦИИ (792300):")
        print(f"1. Отфильтровано по статусу PE: {self.filtered_by_status}")
        print(f"2. Исключено преподавателей: {self.excluded_by_teacher}")
        print(f"3. Исключено филиалов: {self.excluded_by_branch}")
        print(f"4. Итого включено в отчет: {self.final_count}")
        
        # Статистика по форме 2304918 если есть
        if hasattr(self, 'form_2304918_stats'):
            stats_2304918 = self.form_2304918_stats
            print(f"\n🏢 СТАТИСТИКА ПО ЧТЗ (форма 2304918 - возврат студентов):")
            print(f"Всего задач ЧТЗ в Pyrus: {stats_2304918['chtz_tasks']}")
            print(f"\n🔍 ДЕТАЛИЗАЦИЯ ФИЛЬТРАЦИИ (2304918):")
            print(f"1. Отфильтровано по статусу PE: {stats_2304918['filtered_by_status']}")
            print(f"2. Исключено преподавателей: {stats_2304918['excluded_by_teacher']}")
            print(f"3. Исключено филиалов: {stats_2304918['excluded_by_branch']}")
            print(f"4. Итого включено в отчет: {stats_2304918['final_count']}")
        
        # Названия филиалов ЧТЗ
        print(f"\n🏢 НАЗВАНИЯ ФИЛИАЛОВ ЧТЗ:")
        for branch, count in self.raw_branches.most_common():
            print(f"  {branch}: {count}")
        
        # Статусы PE
        print(f"\n📋 СТАТУСЫ PE:")
        for status, count in self.pe_statuses.most_common():
            valid = "✅" if self._is_valid_pe_status(status) else "❌"
            print(f"  {valid} {status}: {count}")
        
        # Исключенные преподаватели
        if self.excluded_teacher_names:
            print(f"\n👨‍🏫 ИСКЛЮЧЕННЫЕ ПРЕПОДАВАТЕЛИ:")
            excluded_counter = Counter(self.excluded_teacher_names)
            for teacher, count in excluded_counter.most_common():
                print(f"  {teacher}: {count}")
        
        # Исключенные филиалы
        if self.excluded_branches:
            print(f"\n🏢 ИСКЛЮЧЕННЫЕ ФИЛИАЛЫ:")
            for branch in set(self.excluded_branches):
                print(f"  {branch}")
        
        # Выводы
        print(f"\n💡 ВЫВОДЫ:")
        expected_discrepancy = self.filtered_by_status + self.excluded_by_teacher + self.excluded_by_branch
        actual_discrepancy = chtz_total - 147
        
        if expected_discrepancy == actual_discrepancy:
            print(f"✅ Расхождение объяснено фильтрацией: {expected_discrepancy}")
        else:
            print(f"❓ Ожидаемое расхождение: {expected_discrepancy}")
            print(f"❓ Фактическое расхождение: {actual_discrepancy}")
            print(f"❓ Необъясненная разница: {actual_discrepancy - expected_discrepancy}")
        
        print(f"\n🎯 ВОЗМОЖНЫЕ ПРИЧИНЫ РАСХОЖДЕНИЯ:")
        print(f"1. Фильтрация по статусу PE (оставляем только PE Start, PE Future, PE 5)")
        print(f"2. Исключения преподавателей из teacher_exclusions.json")
        print(f"3. Исключение определенных филиалов в _normalize_branch_name")
        print(f"4. Возможная фильтрация по дате (не реализована в текущем коде)")
        
        # Детальные списки исключенных форм
        print(f"\n📋 ДЕТАЛЬНЫЕ СПИСКИ ИСКЛЮЧЕННЫХ ФОРМ:")
        
        if hasattr(self, 'excluded_details'):
            # Формы исключенные по статусу PE
            if self.excluded_details['pe_status']:
                print(f"\n❌ ИСКЛЮЧЕНО ПО СТАТУСУ PE ({len(self.excluded_details['pe_status'])}):")
                for task_id, status, teacher, branch in self.excluded_details['pe_status'][:10]:  # Показываем первые 10
                    print(f"  {task_id}: {status} | {teacher} | {branch}")
                if len(self.excluded_details['pe_status']) > 10:
                    print(f"  ... и еще {len(self.excluded_details['pe_status']) - 10}")
            
            # Формы исключенные по преподавателю
            if self.excluded_details['teacher']:
                print(f"\n👨‍🏫 ИСКЛЮЧЕНО ПО ПРЕПОДАВАТЕЛЮ ({len(self.excluded_details['teacher'])}):")
                for task_id, teacher, branch in self.excluded_details['teacher']:
                    print(f"  {task_id}: {teacher} | {branch}")
            
            # Формы исключенные по филиалу
            if self.excluded_details['branch']:
                print(f"\n🏢 ИСКЛЮЧЕНО ПО ФИЛИАЛУ ({len(self.excluded_details['branch'])}):")
                for task_id, branch, teacher in self.excluded_details['branch']:
                    print(f"  {task_id}: {branch} | {teacher}")
            
            # Формы включенные в отчет (для проверки)
            print(f"\n✅ ВКЛЮЧЕНО В ОТЧЕТ 792300 ({len(self.excluded_details['included'])}):")
            for task_id, teacher, branch, status in self.excluded_details['included'][:5]:  # Показываем первые 5
                print(f"  {task_id}: {teacher} | {branch} | {status}")
            if len(self.excluded_details['included']) > 5:
                print(f"  ... и еще {len(self.excluded_details['included']) - 5}")
        
        # Детальные списки для формы 2304918
        if hasattr(self, 'form_2304918_stats') and self.form_2304918_stats['excluded_details']:
            details_2304918 = self.form_2304918_stats['excluded_details']
            
            print(f"\n📋 ДЕТАЛЬНЫЕ СПИСКИ ДЛЯ ФОРМЫ 2304918:")
            
            # Формы исключенные по статусу PE
            if details_2304918['pe_status']:
                print(f"\n❌ ИСКЛЮЧЕНО ПО СТАТУСУ PE 2304918 ({len(details_2304918['pe_status'])}):")
                for task_id, status, teacher, branch in details_2304918['pe_status'][:10]:
                    print(f"  {task_id}: {status} | {teacher} | {branch}")
                if len(details_2304918['pe_status']) > 10:
                    print(f"  ... и еще {len(details_2304918['pe_status']) - 10}")
            
            # Формы исключенные по преподавателю
            if details_2304918['teacher']:
                print(f"\n👨‍🏫 ИСКЛЮЧЕНО ПО ПРЕПОДАВАТЕЛЮ 2304918 ({len(details_2304918['teacher'])}):")
                for task_id, teacher, branch in details_2304918['teacher']:
                    print(f"  {task_id}: {teacher} | {branch}")
            
            # Формы исключенные по филиалу
            if details_2304918['branch']:
                print(f"\n🏢 ИСКЛЮЧЕНО ПО ФИЛИАЛУ 2304918 ({len(details_2304918['branch'])}):")
                for task_id, branch, teacher in details_2304918['branch']:
                    print(f"  {task_id}: {branch} | {teacher}")
            
            # Формы включенные в отчет
            print(f"\n✅ ВКЛЮЧЕНО В ОТЧЕТ 2304918 ({len(details_2304918['included'])}):")
            for task_id, teacher, branch, status in details_2304918['included'][:5]:
                print(f"  {task_id}: {teacher} | {branch} | {status}")
            if len(details_2304918['included']) > 5:
                print(f"  ... и еще {len(details_2304918['included']) - 5}")

        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        print(f"1. Проверить список исключений в teacher_exclusions.json")
        print(f"2. Убедиться в корректности фильтра PE статусов")
        print(f"3. Проверить логику нормализации названий филиалов")
        print(f"4. Рассмотреть добавление фильтрации по дате создания/изменения форм")
        
        print(f"\n🔧 ДЛЯ ИСПРАВЛЕНИЯ РАСХОЖДЕНИЯ:")
        print(f"1. Если нужны все статусы PE - убрать фильтр _is_valid_pe_status")
        print(f"2. Если нужны исключенные преподаватели - очистить teacher_exclusions.json")
        print(f"3. Если нужны исключенные филиалы - изменить _normalize_branch_name")


async def main():
    """Главная функция."""
    print("🚀 Запуск анализа расхождений между отчетом и данными Pyrus...")
    
    try:
        analyzer = DiscrepancyAnalyzer()
        await analyzer.analyze_form_792300()
        await analyzer.analyze_form_2304918()
        analyzer.print_report()
    except KeyboardInterrupt:
        print("\n⏹️ Анализ прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Проверяем переменные окружения
    if not os.getenv("PYRUS_LOGIN") or not os.getenv("PYRUS_SECURITY_KEY"):
        print("❌ ОШИБКА: Не установлены переменные окружения PYRUS_LOGIN и PYRUS_SECURITY_KEY")
        print("Убедитесь, что .env файл настроен корректно.")
        sys.exit(1)
    
    asyncio.run(main())
