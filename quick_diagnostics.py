#!/usr/bin/env python3
"""
Быстрая диагностика PyrusTelegramBot
Проверяет только критически важные компоненты для быстрого выявления проблем
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def check_mark(condition, message):
    """Вывод результата проверки с символом"""
    symbol = "✅" if condition else "❌"
    print(f"{symbol} {message}")
    return condition

def warning_mark(message):
    """Вывод предупреждения"""
    print(f"⚠️ {message}")

def main():
    print("⚡ БЫСТРАЯ ДИАГНОСТИКА PyrusTelegramBot")
    print("=" * 50)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Директория: {Path.cwd()}")
    print("=" * 50)
    
    issues = []
    warnings = []
    
    # 1. Проверка Python и виртуального окружения
    print("\n🐍 PYTHON ОКРУЖЕНИЕ")
    print("-" * 30)
    
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if not check_mark(in_venv, f"Виртуальное окружение активно"):
        issues.append("Виртуальное окружение не активировано")
    
    check_mark(True, f"Python версия: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # 2. Проверка критически важных файлов
    print("\n📁 КРИТИЧЕСКИЕ ФАЙЛЫ")
    print("-" * 30)
    
    critical_files = [
        "requirements.txt",
        ".env",
        "app/__init__.py", 
        "app/api.py",
        "app/bot.py",
        "app/worker.py",
        "app/db.py"
    ]
    
    missing_files = []
    for file_path in critical_files:
        exists = Path(file_path).exists()
        if not check_mark(exists, f"Файл {file_path}"):
            missing_files.append(file_path)
    
    if missing_files:
        issues.append(f"Отсутствуют файлы: {', '.join(missing_files)}")
    
    # 3. Проверка переменных окружения
    print("\n🔐 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ")
    print("-" * 30)
    
    # Загружаем .env если есть
    env_file = Path(".env")
    if env_file.exists():
        check_mark(True, "Файл .env найден")
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            warning_mark("python-dotenv не установлен")
    else:
        check_mark(False, "Файл .env НЕ НАЙДЕН!")
        issues.append("Отсутствует файл .env")
    
    critical_env_vars = [
        "BOT_TOKEN",
        "SUPABASE_URL", 
        "SUPABASE_KEY",
        "PYRUS_LOGIN",
        "PYRUS_SECURITY_KEY"
    ]
    
    missing_env = []
    for var in critical_env_vars:
        value = os.getenv(var)
        if value:
            check_mark(True, f"{var} установлена ({len(value)} символов)")
        else:
            check_mark(False, f"{var} НЕ УСТАНОВЛЕНА!")
            missing_env.append(var)
    
    if missing_env:
        issues.append(f"Отсутствуют переменные: {', '.join(missing_env)}")
    
    # 4. Проверка основных пакетов
    print("\n📦 ОСНОВНЫЕ ПАКЕТЫ")
    print("-" * 30)
    
    critical_packages = [
        "fastapi",
        "uvicorn",
        "python-telegram-bot",
        "supabase", 
        "httpx",
        "python-dotenv"
    ]
    
    missing_packages = []
    for package in critical_packages:
        try:
            __import__(package.replace("-", "_"))
            check_mark(True, f"Пакет {package}")
        except ImportError:
            check_mark(False, f"Пакет {package} НЕ УСТАНОВЛЕН!")
            missing_packages.append(package)
    
    if missing_packages:
        issues.append(f"Отсутствуют пакеты: {', '.join(missing_packages)}")
    
    # 5. Быстрая проверка импорта модулей проекта
    print("\n📥 МОДУЛИ ПРОЕКТА")
    print("-" * 30)
    
    project_modules = ["app.db", "app.bot", "app.api", "app.worker"]
    failed_imports = []
    
    for module in project_modules:
        try:
            __import__(module)
            check_mark(True, f"Импорт {module}")
        except Exception as e:
            check_mark(False, f"Импорт {module}: {str(e)[:50]}...")
            failed_imports.append(module)
    
    if failed_imports:
        issues.append(f"Не импортируются модули: {', '.join(failed_imports)}")
    
    # 6. Проверка сети (базовая)
    print("\n🌐 СЕТЕВОЕ ПОДКЛЮЧЕНИЕ")
    print("-" * 30)
    
    try:
        result = subprocess.run(["ping", "-c", "1", "8.8.8.8"], 
                              capture_output=True, timeout=5)
        internet_ok = result.returncode == 0
        check_mark(internet_ok, "Интернет соединение")
        if not internet_ok:
            issues.append("Нет доступа к интернету")
    except:
        warning_mark("Не удалось проверить интернет соединение")
    
    # 7. Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГИ БЫСТРОЙ ДИАГНОСТИКИ")
    print("=" * 50)
    
    if not issues and not warnings:
        print("🎉 ОТЛИЧНО! Критических проблем не обнаружено")
        print("   Система готова к запуску PyrusTelegramBot")
    else:
        if issues:
            print(f"\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ({len(issues)}):")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
        
        if warnings:
            print(f"\n⚠️ ПРЕДУПРЕЖДЕНИЯ ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                print(f"   {i}. {warning}")
    
    print("\n💡 СЛЕДУЮЩИЕ ШАГИ:")
    if issues:
        print("   1. Исправьте критические проблемы выше")
        print("   2. Запустите полную диагностику: python system_diagnostics.py")
        print("   3. Сравните с рабочей машиной")
    else:
        print("   1. Запустите полную диагностику: python system_diagnostics.py")
        print("   2. Попробуйте запустить бот: python run_stage5.py --bot")
    
    print("=" * 50)
    
    # Возвращаем код выхода
    return 1 if issues else 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

