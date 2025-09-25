#!/usr/bin/env python3
"""
Простая проверка статистики ЧТЗ в измененном коде.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent / "app"))

from pyrus_excel_report import PyrusDataAnalyzer

async def check_chtz_stats():
    """Проверяет статистику ЧТЗ в обновленном коде."""
    print("🔍 Проверка статистики ЧТЗ после изменений...")
    
    analyzer = PyrusDataAnalyzer()
    await analyzer.analyze_form_2304918()
    await analyzer.analyze_form_792300()
    
    # Ищем ЧТЗ в статистике филиалов
    print("\n📊 СТАТИСТИКА ПО ВСЕМ ФИЛИАЛАМ:")
    for branch_name, branch_stats in analyzer.branches_stats.items():
        print(f"{branch_name}:")
        print(f"  2304918: {branch_stats.form_2304918_total} всего, {branch_stats.form_2304918_studying} учится")
        print(f"  792300: {branch_stats.form_792300_total} всего, {branch_stats.form_792300_studying} учится")
        print(f"  Итого %: {branch_stats.total_percentage:.2f}%")
        print()
    
    # Фокус на ЧТЗ
    chtz_branches = [name for name in analyzer.branches_stats.keys() if 'чтз' in name.lower() or 'чит' in name.lower()]
    if chtz_branches:
        print("\n🎯 СТАТИСТИКА ЧТЗ:")
        for branch_name in chtz_branches:
            branch_stats = analyzer.branches_stats[branch_name]
            print(f"Филиал: {branch_name}")
            print(f"  Форма 2304918: {branch_stats.form_2304918_total} форм")
            print(f"  Форма 792300: {branch_stats.form_792300_total} форм")
            print(f"  Итого форм: {branch_stats.form_2304918_total + branch_stats.form_792300_total}")
            print(f"  Ожидалось: 160 (по условию задачи)")
            print(f"  Разница: {(branch_stats.form_2304918_total + branch_stats.form_792300_total) - 160}")
    else:
        print("❌ ЧТЗ не найден в статистике филиалов!")

if __name__ == "__main__":
    asyncio.run(check_chtz_stats())


