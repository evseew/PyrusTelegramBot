#!/usr/bin/env python3
"""
Проверка влияния исключений преподавателей на все филиалы.
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Dict, Set
from collections import defaultdict, Counter
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent / "app"))

from pyrus_client import PyrusClient

class BranchExclusionAnalyzer:
    """Анализатор влияния исключений на все филиалы."""
    
    def __init__(self):
        self.client = PyrusClient()
        self.excluded_teachers = self._load_exclusions()
        
        # Статистика по филиалам: ДО и ПОСЛЕ исключений
        self.branches_before = defaultdict(lambda: {'2304918': 0, '792300': 0})
        self.branches_after = defaultdict(lambda: {'2304918': 0, '792300': 0})
        
        # Детализация исключенных форм по филиалам
        self.excluded_by_branch = defaultdict(lambda: {'2304918': [], '792300': []})
    
    def _load_exclusions(self) -> Dict[str, Set[str]]:
        """Загружает списки исключений преподавателей."""
        exclusions_file = Path(__file__).parent / "teacher_exclusions.json"
        try:
            with open(exclusions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'oldies': set(data.get('oldies', [])),
                    'trial': set(data.get('trial', []))
                }
        except Exception:
            return {'oldies': set(), 'trial': set()}
    
    def _get_field_value(self, field_list, field_id):
        """Извлекает значение поля."""
        for f in field_list or []:
            if f.get("id") == field_id:
                return f.get("value")
            val = f.get("value")
            if isinstance(val, dict) and isinstance(val.get("fields"), list):
                nested = self._get_field_value(val.get("fields") or [], field_id)
                if nested is not None:
                    return nested
        return None
    
    def _extract_branch_name(self, task_fields, field_id):
        """Извлекает название филиала."""
        value = self._get_field_value(task_fields, field_id)
        raw_name = "Неизвестный филиал"
        
        if isinstance(value, dict):
            values = value.get("values")
            if isinstance(values, list) and len(values) > 0:
                raw_name = values[0]
            elif not raw_name or raw_name == "Неизвестный филиал":
                rows = value.get("rows")
                if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], list):
                    raw_name = rows[0][0] if len(rows[0]) > 0 else raw_name
            
            if raw_name == "Неизвестный филиал":
                for key in ("text", "name", "value"):
                    branch_val = value.get(key)
                    if isinstance(branch_val, str) and branch_val.strip():
                        raw_name = branch_val.strip()
                        break
        
        if isinstance(value, str):
            raw_name = value.strip()
        
        return self._normalize_branch_name(raw_name)
    
    def _normalize_branch_name(self, branch_name):
        """Нормализует название филиала."""
        if not branch_name or branch_name == "Неизвестный филиал":
            return None
            
        branch_name_lower = branch_name.lower().strip()
        
        # Исключения
        if "макеева" in branch_name_lower and "15" in branch_name_lower:
            return None
        if "коммуны" in branch_name_lower and "106/1" in branch_name_lower:
            return None
        
        # Объединения
        if "коммунистический" in branch_name_lower and "22" in branch_name_lower:
            return "Копейск"
        if "славы" in branch_name_lower and "30" in branch_name_lower:
            return "Копейск"
        
        return branch_name.title()
    
    def _extract_teacher_name(self, task_fields, field_id):
        """Извлекает ФИО преподавателя."""
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
        
        return "Неизвестный преподаватель"
    
    def _is_teacher_excluded(self, teacher_name, form_type):
        """Проверяет исключения преподавателей."""
        excluded_set = self.excluded_teachers.get(form_type, set())
        
        if teacher_name in excluded_set:
            return True
        
        for excluded_name in excluded_set:
            if excluded_name.lower() in teacher_name.lower():
                return True
        
        return False
    
    def _is_valid_pe_status(self, task_fields, field_id):
        """Проверяет валидность статуса PE."""
        value = self._get_field_value(task_fields, field_id)
        valid_statuses = {"PE Start", "PE Future", "PE 5"}
        
        if isinstance(value, dict):
            choice_names = value.get("choice_names")
            if isinstance(choice_names, list) and len(choice_names) > 0:
                return choice_names[0] in valid_statuses
            
            values = value.get("values")
            if isinstance(values, list) and len(values) > 0:
                return values[0] in valid_statuses
            
            rows = value.get("rows")
            if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], list):
                return len(rows[0]) > 0 and rows[0][0] in valid_statuses
            
            for key in ("text", "name", "value"):
                status_val = value.get(key)
                if isinstance(status_val, str):
                    return status_val.strip() in valid_statuses
        
        if isinstance(value, str):
            return value.strip() in valid_statuses
        
        return False
    
    async def analyze_form(self, form_id, form_name, teacher_field_id, branch_field_id, status_field_id, exclusion_type):
        """Анализирует влияние исключений на филиалы для одной формы."""
        print(f"🔍 Анализ формы {form_id} ({form_name})...")
        
        task_count = 0
        
        async for task in self.client.iter_register_tasks(form_id, include_archived=False):
            task_count += 1
            if task_count % 100 == 0:
                print(f"Обработано {task_count} задач...")
            
            task_fields = task.get("fields", [])
            task_id = task.get("id")
            
            # Фильтр PE статуса
            if not self._is_valid_pe_status(task_fields, status_field_id):
                continue
            
            # Извлекаем данные
            teacher_name = self._extract_teacher_name(task_fields, teacher_field_id)
            branch_name = self._extract_branch_name(task_fields, branch_field_id)
            
            if branch_name is None:
                continue
            
            # Считаем ДО исключений
            self.branches_before[branch_name][str(form_id)] += 1
            
            # Проверяем исключения
            if self._is_teacher_excluded(teacher_name, exclusion_type):
                # Запоминаем исключенную форму
                self.excluded_by_branch[branch_name][str(form_id)].append({
                    'task_id': task_id,
                    'teacher': teacher_name
                })
            else:
                # Считаем ПОСЛЕ исключений
                self.branches_after[branch_name][str(form_id)] += 1
        
        print(f"✅ Анализ формы {form_id} завершен. Обработано {task_count} задач.")
    
    async def run_analysis(self):
        """Запускает полный анализ."""
        print("🚀 Анализ влияния исключений преподавателей на все филиалы...")
        
        # Анализируем обе формы
        await self.analyze_form(
            form_id=2304918,
            form_name="возврат студентов",
            teacher_field_id=8,
            branch_field_id=5,
            status_field_id=7,
            exclusion_type='oldies'
        )
        
        await self.analyze_form(
            form_id=792300,
            form_name="конверсия trial",
            teacher_field_id=142,
            branch_field_id=226,
            status_field_id=228,
            exclusion_type='trial'
        )
        
        self.print_report()
    
    def print_report(self):
        """Выводит отчет по влиянию исключений."""
        print("\n" + "="*80)
        print("📊 ВЛИЯНИЕ ИСКЛЮЧЕНИЙ ПРЕПОДАВАТЕЛЕЙ НА ВСЕ ФИЛИАЛЫ")
        print("="*80)
        
        total_lost_2304918 = 0
        total_lost_792300 = 0
        
        print(f"\n{'Филиал':<30} {'2304918 ДО':<12} {'2304918 ПОСЛЕ':<15} {'Потеряно':<10} {'792300 ДО':<12} {'792300 ПОСЛЕ':<15} {'Потеряно':<10}")
        print("-" * 120)
        
        all_branches = set(self.branches_before.keys()) | set(self.branches_after.keys())
        
        for branch in sorted(all_branches):
            before_2304918 = self.branches_before[branch]['2304918']
            after_2304918 = self.branches_after[branch]['2304918']
            lost_2304918 = before_2304918 - after_2304918
            
            before_792300 = self.branches_before[branch]['792300']
            after_792300 = self.branches_after[branch]['792300']
            lost_792300 = before_792300 - after_792300
            
            total_lost_2304918 += lost_2304918
            total_lost_792300 += lost_792300
            
            print(f"{branch:<30} {before_2304918:<12} {after_2304918:<15} {lost_2304918:<10} {before_792300:<12} {after_792300:<15} {lost_792300:<10}")
        
        print("-" * 120)
        print(f"{'ИТОГО ПОТЕРЯНО:':<30} {'':<12} {'':<15} {total_lost_2304918:<10} {'':<12} {'':<15} {total_lost_792300:<10}")
        
        # Детализация по исключенным преподавателям
        print(f"\n📋 ДЕТАЛИЗАЦИЯ ИСКЛЮЧЕННЫХ ФОРМ:")
        
        for branch in sorted(all_branches):
            excluded_2304918 = self.excluded_by_branch[branch]['2304918']
            excluded_792300 = self.excluded_by_branch[branch]['792300']
            
            if excluded_2304918 or excluded_792300:
                print(f"\n🏢 {branch}:")
                
                if excluded_2304918:
                    print(f"  Форма 2304918 - исключено {len(excluded_2304918)} форм:")
                    teacher_counts = Counter(item['teacher'] for item in excluded_2304918)
                    for teacher, count in teacher_counts.most_common():
                        print(f"    {teacher}: {count} форм")
                
                if excluded_792300:
                    print(f"  Форма 792300 - исключено {len(excluded_792300)} форм:")
                    teacher_counts = Counter(item['teacher'] for item in excluded_792300)
                    for teacher, count in teacher_counts.most_common():
                        print(f"    {teacher}: {count} форм")

async def main():
    """Главная функция."""
    analyzer = BranchExclusionAnalyzer()
    await analyzer.run_analysis()

if __name__ == "__main__":
    asyncio.run(main())


