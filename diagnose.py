#!/usr/bin/env python3
"""
Основной скрипт диагностики PyrusTelegramBot
Интерактивный помощник для запуска различных видов диагностики
"""
import os
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

def run_command(cmd):
    """Запуск команды с выводом результата"""
    print(f"🚀 Выполняется: {' '.join(cmd)}")
    print("-" * 50)
    result = subprocess.run(cmd, text=True)
    print("-" * 50)
    return result.returncode == 0

def interactive_menu():
    """Интерактивное меню диагностики"""
    print("""
🔍 ДИАГНОСТИКА PyrusTelegramBot
================================

Выберите тип диагностики:

1. 🏃‍♂️ Быстрая диагностика (10-15 сек)
   Проверяет только критически важные компоненты

2. 🔬 Полная диагностика (30-60 сек)
   Комплексная проверка всех аспектов системы

3. 📊 Сравнение с другой машиной
   Сравнивает результаты диагностики между машинами

4. 📖 Показать инструкции
   Подробное руководство по использованию

5. 🛠️ Проверить конкретную проблему
   Целевая диагностика определенного компонента

0. ❌ Выход

Ваш выбор: """, end="")
    
    choice = input().strip()
    return choice

def quick_diagnostics():
    """Запуск быстрой диагностики"""
    print("\n⚡ ЗАПУСК БЫСТРОЙ ДИАГНОСТИКИ")
    print("=" * 50)
    
    python_cmd = get_python_command()
    if not python_cmd:
        return False
    
    return run_command([python_cmd, "quick_diagnostics.py"])

def full_diagnostics():
    """Запуск полной диагностики"""
    print("\n🔬 ЗАПУСК ПОЛНОЙ ДИАГНОСТИКИ")
    print("=" * 50)
    
    python_cmd = get_python_command()
    if not python_cmd:
        return False
    
    success = run_command([python_cmd, "system_diagnostics.py"])
    
    if success:
        # Находим последний созданный отчет
        reports = list(Path(".").glob("diagnostic_report_*.json"))
        if reports:
            latest_report = max(reports, key=lambda p: p.stat().st_mtime)
            print(f"\n📄 Отчет сохранен: {latest_report}")
            print("💡 Для сравнения с другой машиной используйте опцию 3")
    
    return success

def compare_diagnostics():
    """Сравнение диагностики между машинами"""
    print("\n📊 СРАВНЕНИЕ ДИАГНОСТИКИ")
    print("=" * 50)
    
    # Ищем JSON отчеты
    reports = list(Path(".").glob("diagnostic_report_*.json"))
    
    if len(reports) < 1:
        print("❌ Не найдено ни одного отчета диагностики!")
        print("💡 Сначала запустите полную диагностику (опция 2)")
        return False
    
    if len(reports) == 1:
        print("📄 Найден один отчет диагностики:")
        print(f"   {reports[0]}")
        print("\n❓ Для сравнения нужны отчеты с двух машин.")
        print("💡 Инструкция:")
        print("   1. Скопируйте этот отчет на другую машину")
        print("   2. Запустите диагностику на второй машине")  
        print("   3. Используйте скрипт compare_diagnostics.py")
        
        return True
    
    # Если есть несколько отчетов, выбираем два последних
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    print("📄 Найдено отчетов диагностики:")
    for i, report in enumerate(reports[:5], 1):
        mtime = datetime.fromtimestamp(report.stat().st_mtime)
        print(f"   {i}. {report} ({mtime.strftime('%Y-%m-%d %H:%M:%S')})")
    
    if len(reports) >= 2:
        print(f"\n🔄 Сравниваем два последних отчета:")
        print(f"   Отчет 1: {reports[1]}")
        print(f"   Отчет 2: {reports[0]}")
        
        python_cmd = get_python_command()
        if not python_cmd:
            return False
        
        return run_command([
            python_cmd, "compare_diagnostics.py",
            str(reports[1]), str(reports[0]),
            "--name1", "Более старый",
            "--name2", "Более новый"
        ])
    
    return True

def show_instructions():
    """Показать подробные инструкции"""
    readme_path = Path("DIAGNOSTICS_README.md")
    
    if readme_path.exists():
        print("\n📖 ПОДРОБНЫЕ ИНСТРУКЦИИ")
        print("=" * 50)
        
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Показываем только основную часть (первые 100 строк)
            lines = content.split('\n')
            for line in lines[:100]:
                print(line)
            
            if len(lines) > 100:
                print("\n... (показаны первые 100 строк)")
                print(f"📄 Полные инструкции в файле: {readme_path}")
        
        except Exception as e:
            print(f"❌ Ошибка чтения инструкций: {e}")
            return False
    else:
        print("❌ Файл с инструкциями не найден!")
        return False
    
    return True

def targeted_diagnostics():
    """Целевая диагностика конкретных проблем"""
    print("\n🛠️ ЦЕЛЕВАЯ ДИАГНОСТИКА")
    print("=" * 50)
    
    problems = {
        "1": ("Проблемы с импортом модулей", check_imports),
        "2": ("Проблемы с переменными окружения", check_environment),
        "3": ("Проблемы с API подключениями", check_apis),
        "4": ("Проблемы с пакетами Python", check_packages),
        "5": ("Проблемы с правами доступа", check_permissions)
    }
    
    print("Выберите проблему для диагностики:")
    for key, (description, _) in problems.items():
        print(f"   {key}. {description}")
    print("   0. Назад")
    
    choice = input("\nВаш выбор: ").strip()
    
    if choice == "0":
        return True
    
    if choice in problems:
        description, func = problems[choice]
        print(f"\n🔍 Диагностика: {description}")
        print("-" * 50)
        return func()
    else:
        print("❌ Неверный выбор!")
        return False

def check_imports():
    """Проверка импортов"""
    modules = [
        "fastapi", "uvicorn", "telegram", "supabase", 
        "httpx", "pandas", "openpyxl", "dotenv",
        "app.api", "app.bot", "app.worker", "app.db"
    ]
    
    failed = []
    
    for module in modules:
        try:
            __import__(module.replace("-", "_"))
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n🔧 Для исправления:")
        print("pip install " + " ".join(f for f in failed if not f.startswith("app.")))
    
    return len(failed) == 0

def check_environment():
    """Проверка переменных окружения"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("❌ python-dotenv не установлен")
        return False
    
    required_vars = [
        "BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY",
        "PYRUS_LOGIN", "PYRUS_SECURITY_KEY"
    ]
    
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: установлена ({len(value)} символов)")
        else:
            print(f"❌ {var}: НЕ УСТАНОВЛЕНА")
            missing.append(var)
    
    if missing:
        print(f"\n🔧 Добавьте в .env файл:")
        for var in missing:
            print(f"{var}=your_value_here")
    
    return len(missing) == 0

def check_apis():
    """Проверка API подключений"""
    import asyncio
    
    async def test_apis():
        try:
            import httpx
            
            apis = []
            
            bot_token = os.getenv("BOT_TOKEN")
            if bot_token:
                apis.append(("Telegram Bot API", f"https://api.telegram.org/bot{bot_token}/getMe"))
            
            supabase_url = os.getenv("SUPABASE_URL")
            if supabase_url:
                apis.append(("Supabase", f"{supabase_url}/rest/v1/"))
            
            async with httpx.AsyncClient(timeout=10) as client:
                for name, url in apis:
                    try:
                        response = await client.get(url)
                        if response.status_code < 400:
                            print(f"✅ {name}: доступен")
                        else:
                            print(f"❌ {name}: HTTP {response.status_code}")
                    except Exception as e:
                        print(f"❌ {name}: {e}")
        
        except ImportError:
            print("❌ httpx не установлен")
            return False
    
    try:
        asyncio.run(test_apis())
        return True
    except Exception as e:
        print(f"❌ Ошибка проверки API: {e}")
        return False

def check_packages():
    """Проверка пакетов"""
    try:
        with open("requirements.txt", "r") as f:
            required = [line.strip().split("==")[0] for line in f if line.strip() and not line.startswith("#")]
        
        missing = []
        for package in required:
            try:
                __import__(package.replace("-", "_"))
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package}: не установлен")
                missing.append(package)
        
        if missing:
            print(f"\n🔧 Установите: pip install {' '.join(missing)}")
        
        return len(missing) == 0
        
    except FileNotFoundError:
        print("❌ requirements.txt не найден")
        return False

def check_permissions():
    """Проверка прав доступа"""
    files_to_check = [
        "app/", ".env", "requirements.txt", "logs/"
    ]
    
    issues = []
    
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            readable = os.access(path, os.R_OK)
            writable = os.access(path, os.W_OK)
            
            status = "✅" if readable and writable else "❌"
            perms = f"{'r' if readable else '-'}{'w' if writable else '-'}"
            print(f"{status} {file_path}: {perms}")
            
            if not readable or not writable:
                issues.append(file_path)
        else:
            print(f"⚪ {file_path}: не найден")
    
    if issues:
        print(f"\n🔧 Исправьте права: chmod -R 755 {' '.join(issues)}")
    
    return len(issues) == 0

def get_python_command():
    """Определяет команду для запуска Python"""
    for cmd in ["python3", "python"]:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return cmd
        except FileNotFoundError:
            continue
    
    print("❌ Python не найден! Установите Python 3.7+")
    return None

def check_prerequisites():
    """Проверка предварительных условий"""
    # Проверяем, что мы в правильной директории
    required_files = ["app/", "requirements.txt"]
    missing = [f for f in required_files if not Path(f).exists()]
    
    if missing:
        print(f"❌ Вы не в директории проекта PyrusTelegramBot!")
        print(f"   Отсутствуют: {', '.join(missing)}")
        print("💡 Перейдите в корневую директорию проекта")
        return False
    
    # Проверяем Python
    if not get_python_command():
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Диагностика PyrusTelegramBot")
    parser.add_argument("--quick", action="store_true", help="Быстрая диагностика")
    parser.add_argument("--full", action="store_true", help="Полная диагностика") 
    parser.add_argument("--compare", action="store_true", help="Сравнение отчетов")
    parser.add_argument("--help-docs", action="store_true", help="Показать инструкции")
    
    args = parser.parse_args()
    
    # Проверяем предварительные условия
    if not check_prerequisites():
        sys.exit(1)
    
    print("🔍 ДИАГНОСТИКА PyrusTelegramBot")
    print("=" * 50)
    print(f"📁 Директория: {Path.cwd()}")
    print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Обработка аргументов командной строки
    if args.quick:
        return 0 if quick_diagnostics() else 1
    elif args.full:
        return 0 if full_diagnostics() else 1
    elif args.compare:
        return 0 if compare_diagnostics() else 1
    elif args.help_docs:
        return 0 if show_instructions() else 1
    
    # Интерактивный режим
    while True:
        choice = interactive_menu()
        
        if choice == "0":
            print("\n👋 До свидания!")
            break
        elif choice == "1":
            quick_diagnostics()
        elif choice == "2":
            full_diagnostics()
        elif choice == "3":
            compare_diagnostics()
        elif choice == "4":
            show_instructions()
        elif choice == "5":
            targeted_diagnostics()
        else:
            print("❌ Неверный выбор! Попробуйте еще раз.")
        
        input("\n⏎ Нажмите Enter для продолжения...")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Диагностика прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)

