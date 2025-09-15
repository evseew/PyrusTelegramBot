#!/usr/bin/env python3
"""
Скрипт для проверки конкретной задачи Pyrus и анализа правил валидации.
Использует существующие PyrusClient и правила валидации.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

# Загружаем переменные окружения
load_dotenv()

from app.pyrus_client import PyrusClient
from app.rules.form_2304918 import check_rules as check_rules_2304918
from app.rules.form_792300 import check_rules as check_rules_792300

def _build_fields_meta(form_meta: dict) -> dict:
    """Строит метаданные полей формы"""
    out = {}
    for f in form_meta.get("fields", []) or []:
        fid = f.get("id")
        if isinstance(fid, int):
            out[fid] = {"name": f.get("name"), "type": f.get("type")}
    return out

def print_field_value(field_id: int, value, fields_meta: dict):
    """Выводит значение поля в читаемом виде"""
    field_name = fields_meta.get(field_id, {}).get("name", f"Поле {field_id}")
    
    if value is None:
        print(f"  [{field_id}] {field_name}: <пустое>")
    elif isinstance(value, dict):
        if "checkmark" in value:
            status = "✓" if value.get("checkmark") == "checked" else "✗"
            print(f"  [{field_id}] {field_name}: {status}")
        elif "choice_names" in value:
            choices = value.get("choice_names", [])
            print(f"  [{field_id}] {field_name}: {choices}")
        elif "text" in value:
            print(f"  [{field_id}] {field_name}: \"{value.get('text')}\"")
        elif "date" in value:
            print(f"  [{field_id}] {field_name}: {value.get('date')}")
        else:
            print(f"  [{field_id}] {field_name}: {value}")
    else:
        print(f"  [{field_id}] {field_name}: {value}")

async def check_task_details(task_id: int):
    """Получает и анализирует данные задачи"""
    print(f"🔍 Проверка задачи #{task_id}")
    print("=" * 60)
    
    client = PyrusClient()
    
    # Получаем данные задачи
    task_data = await client.get_task(task_id)
    if not task_data:
        print(f"❌ Не удалось получить данные задачи #{task_id}")
        return
    
    print(f"📋 Заголовок: {task_data.get('subject') or task_data.get('text', 'Без заголовка')}")
    
    # Определяем форму из списков (added_list_ids) или других полей
    form_id = None
    
    # Ищем в комментариях added_list_ids
    for comment in task_data.get("comments", []):
        added_lists = comment.get("added_list_ids", [])
        if added_lists:
            form_id = added_lists[0]  # Берем первый ID формы
            print(f"🔍 Найден form_id в added_list_ids: {form_id}")
            break
    
    # Fallback: другие возможные поля
    if not form_id:
        form_id = (task_data.get("form_id") or 
                   task_data.get("form", {}).get("id") or
                   task_data.get("structure_id") or
                   task_data.get("structure", {}).get("id"))
        if form_id:
            print(f"🔍 Найден form_id в основных полях: {form_id}")
    
    # Прямое задание для известных задач (временно для отладки)
    if not form_id and task_id in [304880953, 305956884]:
        form_id = 792300
        print(f"🔍 Используем известный form_id для задачи {task_id}: {form_id}")
    
    if not form_id:
        print("❌ Не удалось определить ID формы")
        return
    
    print(f"📝 Форма ID: {form_id}")
    
    # Получаем метаданные формы
    form_meta = await client.get_form_meta(form_id)
    if not form_meta:
        print(f"❌ Не удалось получить метаданные формы {form_id}")
        return
    
    form_name = form_meta.get("name", f"Форма {form_id}")
    print(f"📄 Название формы: {form_name}")
    
    fields_meta = _build_fields_meta(form_meta)
    
    # Извлекаем поля задачи (они в корне ответа)
    task_fields = task_data.get("fields", [])
    print(f"\n📊 Найдено полей в task_data.fields: {len(task_fields)}")
    
    # Если в task_data.fields пусто, поля могут быть в task.fields
    if not task_fields and "task" in task_data:
        task_fields = task_data["task"].get("fields", [])
        print(f"📊 Найдено полей в task_data.task.fields: {len(task_fields)}")
    
    # DEBUG: показываем ключи верхнего уровня
    print(f"🔍 Ключи в task_data: {list(task_data.keys())}")
    
    # Показываем все поля с данными
    print("\n🔎 ДАННЫЕ ПОЛЕЙ:")
    print("-" * 40)
    for field in task_fields:
        field_id = field.get("id")
        value = field.get("value")
        if field_id and value is not None:
            print_field_value(field_id, value, fields_meta)
    
    # Проверяем правила валидации
    print(f"\n✅ ПРОВЕРКА ПРАВИЛ ВАЛИДАЦИИ:")
    print("-" * 40)
    
    # Используем дату БПЗ как target_day (14 сентября)
    target_day = "2025-09-14"
    print(f"Целевая дата: {target_day}")
    
    try:
        if form_id == 2304918:
            errors_map = check_rules_2304918(fields_meta, task_fields, target_day, "today21")
        elif form_id == 792300:
            errors_map = check_rules_792300(fields_meta, task_fields, target_day, "today21")
        else:
            print(f"⚠️ Форма {form_id} не поддерживается для проверки правил")
            return
        
        general_errors = errors_map.get("general", [])
        rule3_errors = errors_map.get("rule3", [])
        
        if general_errors:
            print("\n🚨 ОБЩИЕ ОШИБКИ:")
            for i, error in enumerate(general_errors, 1):
                print(f"  {i}. {error}")
        
        if rule3_errors:
            print("\n🎯 ОШИБКИ ПРАВИЛА 3:")
            for i, error in enumerate(rule3_errors, 1):
                print(f"  {i}. {error}")
        
        if not general_errors and not rule3_errors:
            print("✅ Нарушений правил не найдено!")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке правил: {e}")
    
    print("\n" + "=" * 60)

async def main():
    if len(sys.argv) != 2:
        print("Использование: python check_task.py <TASK_ID>")
        print("Пример: python check_task.py 304880953")
        sys.exit(1)
    
    try:
        task_id = int(sys.argv[1])
    except ValueError:
        print("❌ ID задачи должен быть числом")
        sys.exit(1)
    
    await check_task_details(task_id)

if __name__ == "__main__":
    asyncio.run(main())
