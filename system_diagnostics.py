#!/usr/bin/env python3
"""
Комплексная диагностика PyrusTelegramBot
Проверяет все аспекты системы для выявления различий между рабочей и проблемной машинами
"""
import asyncio
import importlib
import json
import logging
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemDiagnostics:
    """Класс для проведения полной диагностики системы"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {},
            "python_info": {},
            "environment": {},
            "packages": {},
            "files": {},
            "api_connectivity": {},
            "imports": {},
            "permissions": {},
            "logs": {},
            "database": {},
            "network": {},
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
    def log_error(self, message: str, exception: Exception = None):
        """Записать ошибку в результаты"""
        error_msg = f"❌ {message}"
        if exception:
            error_msg += f": {str(exception)}"
        
        self.results["errors"].append(error_msg)
        logger.error(error_msg)
        if exception:
            logger.error(traceback.format_exc())
    
    def log_warning(self, message: str):
        """Записать предупреждение в результаты"""
        warning_msg = f"⚠️ {message}"
        self.results["warnings"].append(warning_msg)
        logger.warning(warning_msg)
    
    def log_success(self, message: str):
        """Записать успешный результат"""
        success_msg = f"✅ {message}"
        logger.info(success_msg)
    
    def run_command(self, command: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Безопасное выполнение команды с таймаутом"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Команда превысила таймаут {timeout}с"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_system_info(self):
        """1. Проверка информации о системе"""
        print("\n🖥️  1. СИСТЕМНАЯ ИНФОРМАЦИЯ")
        print("=" * 50)
        
        try:
            system_info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "username": os.getenv("USER", "unknown"),
                "home_dir": str(Path.home()),
                "current_dir": str(Path.cwd()),
                "path_env": os.getenv("PATH", "").split(os.pathsep)[:10]  # Первые 10 путей
            }
            
            self.results["system_info"] = system_info
            
            print(f"Платформа: {system_info['platform']}")
            print(f"Система: {system_info['system']} {system_info['release']}")
            print(f"Хост: {system_info['hostname']}")
            print(f"Пользователь: {system_info['username']}")
            print(f"Текущая директория: {system_info['current_dir']}")
            
            self.log_success("Системная информация собрана")
            
        except Exception as e:
            self.log_error("Ошибка сбора системной информации", e)

    def check_python_info(self):
        """2. Проверка Python и виртуального окружения"""
        print("\n🐍 2. PYTHON И ВИРТУАЛЬНОЕ ОКРУЖЕНИЕ")
        print("=" * 50)
        
        try:
            python_info = {
                "version": sys.version,
                "version_info": sys.version_info,
                "executable": sys.executable,
                "prefix": sys.prefix,
                "base_prefix": getattr(sys, 'base_prefix', sys.prefix),
                "in_virtualenv": hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
                "path": sys.path[:10]  # Первые 10 путей
            }
            
            self.results["python_info"] = python_info
            
            print(f"Версия Python: {python_info['version_info']}")
            print(f"Исполняемый файл: {python_info['executable']}")
            print(f"Виртуальное окружение: {'✅ Да' if python_info['in_virtualenv'] else '❌ Нет'}")
            
            # Проверка pip
            pip_result = self.run_command([sys.executable, "-m", "pip", "--version"])
            if pip_result["success"]:
                print(f"pip: {pip_result['stdout']}")
                python_info["pip_version"] = pip_result["stdout"]
            else:
                self.log_error("pip не найден или не работает", Exception(pip_result.get("error", "unknown")))
            
            self.log_success("Информация о Python собрана")
            
        except Exception as e:
            self.log_error("Ошибка проверки Python", e)

    def check_environment_variables(self):
        """3. Проверка переменных окружения и .env файла"""
        print("\n🔐 3. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ")
        print("=" * 50)
        
        # Критически важные переменные для проекта
        required_vars = [
            "BOT_TOKEN",
            "ADMIN_IDS", 
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "PYRUS_LOGIN",
            "PYRUS_SECURITY_KEY",
            "PYRUS_WEBHOOK_SECRET",
        ]
        
        optional_vars = [
            "DELAY_HOURS",
            "REPEAT_INTERVAL_HOURS", 
            "TTL_HOURS",
            "TZ",
            "QUIET_START",
            "QUIET_END",
            "DEV_SKIP_PYRUS_SIG",
            "ENV",
            "PYRUS_API_URL"
        ]
        
        try:
            # Загружаем .env файл если есть
            env_file_path = Path(".env")
            env_vars = {}
            
            if env_file_path.exists():
                try:
                    from dotenv import load_dotenv
                    load_dotenv()
                    
                    with open(env_file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                env_vars[key.strip()] = len(value.strip())  # Сохраняем только длину
                    
                    print(f"✅ Файл .env найден ({len(env_vars)} переменных)")
                    
                except Exception as e:
                    self.log_error(f"Ошибка чтения .env файла", e)
            else:
                self.log_warning("Файл .env не найден")
            
            # Проверяем критически важные переменные
            environment = {
                "env_file_exists": env_file_path.exists(),
                "env_file_vars": env_vars,
                "required_vars": {},
                "optional_vars": {},
                "missing_required": [],
                "missing_optional": []
            }
            
            print("\nКритически важные переменные:")
            for var in required_vars:
                value = os.getenv(var)
                if value:
                    environment["required_vars"][var] = len(value)
                    print(f"  ✅ {var}: установлена ({len(value)} символов)")
                else:
                    environment["missing_required"].append(var)
                    print(f"  ❌ {var}: НЕ УСТАНОВЛЕНА!")
            
            print("\nДополнительные переменные:")
            for var in optional_vars:
                value = os.getenv(var)
                if value:
                    environment["optional_vars"][var] = value
                    print(f"  ✅ {var}: {value}")
                else:
                    environment["missing_optional"].append(var)
                    print(f"  ⚪ {var}: не установлена (будет использовано значение по умолчанию)")
            
            self.results["environment"] = environment
            
            if environment["missing_required"]:
                self.log_error(f"Отсутствуют критически важные переменные: {', '.join(environment['missing_required'])}")
            else:
                self.log_success("Все критически важные переменные окружения настроены")
                
        except Exception as e:
            self.log_error("Ошибка проверки переменных окружения", e)

    def check_packages(self):
        """4. Проверка установленных пакетов"""
        print("\n📦 4. УСТАНОВЛЕННЫЕ ПАКЕТЫ")
        print("=" * 50)
        
        try:
            # Читаем requirements.txt
            req_file = Path("requirements.txt")
            required_packages = {}
            
            if req_file.exists():
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '==' in line:
                                name, version = line.split('==', 1)
                                required_packages[name.strip()] = version.strip()
                            else:
                                required_packages[line] = "любая"
                
                print(f"✅ requirements.txt найден ({len(required_packages)} пакетов)")
            else:
                self.log_warning("requirements.txt не найден")
            
            # Получаем список установленных пакетов
            pip_list = self.run_command([sys.executable, "-m", "pip", "list", "--format=json"])
            installed_packages = {}
            
            if pip_list["success"]:
                try:
                    packages_data = json.loads(pip_list["stdout"])
                    installed_packages = {pkg["name"]: pkg["version"] for pkg in packages_data}
                    print(f"✅ Установлено пакетов: {len(installed_packages)}")
                except json.JSONDecodeError:
                    self.log_error("Ошибка парсинга списка пакетов")
            
            # Сравниваем требуемые и установленные пакеты
            packages_status = {
                "required": required_packages,
                "installed": installed_packages,
                "missing": [],
                "version_mismatch": [],
                "extra": []
            }
            
            print("\nСостояние пакетов:")
            for req_pkg, req_version in required_packages.items():
                if req_pkg in installed_packages:
                    installed_version = installed_packages[req_pkg]
                    if req_version == "любая" or req_version == installed_version:
                        print(f"  ✅ {req_pkg}: {installed_version}")
                    else:
                        print(f"  ⚠️ {req_pkg}: требуется {req_version}, установлена {installed_version}")
                        packages_status["version_mismatch"].append({
                            "package": req_pkg,
                            "required": req_version,
                            "installed": installed_version
                        })
                else:
                    print(f"  ❌ {req_pkg}: НЕ УСТАНОВЛЕН!")
                    packages_status["missing"].append(req_pkg)
            
            self.results["packages"] = packages_status
            
            if packages_status["missing"]:
                self.log_error(f"Отсутствуют пакеты: {', '.join(packages_status['missing'])}")
            
            if packages_status["version_mismatch"]:
                self.log_warning(f"Несоответствие версий: {len(packages_status['version_mismatch'])} пакетов")
            
            if not packages_status["missing"] and not packages_status["version_mismatch"]:
                self.log_success("Все требуемые пакеты установлены с правильными версиями")
                
        except Exception as e:
            self.log_error("Ошибка проверки пакетов", e)

    def check_files_and_permissions(self):
        """5. Проверка файлов проекта и прав доступа"""
        print("\n📁 5. ФАЙЛЫ И ПРАВА ДОСТУПА")
        print("=" * 50)
        
        required_files = [
            "app/__init__.py",
            "app/api.py", 
            "app/bot.py",
            "app/worker.py",
            "app/db.py",
            "app/utils.py",
            "app/models.py",
            "app/pyrus_client.py",
            "requirements.txt",
            "run_stage5.py"
        ]
        
        optional_files = [
            ".env",
            "schema.sql",
            "logs/",
            "venv/",
            "__pycache__/"
        ]
        
        try:
            files_status = {
                "required": {},
                "optional": {},
                "missing_required": [],
                "missing_optional": [],
                "permission_issues": []
            }
            
            print("Критически важные файлы:")
            for file_path in required_files:
                path = Path(file_path)
                if path.exists():
                    stat = path.stat()
                    files_status["required"][file_path] = {
                        "exists": True,
                        "size": stat.st_size,
                        "readable": os.access(path, os.R_OK),
                        "writable": os.access(path, os.W_OK),
                        "executable": os.access(path, os.X_OK) if path.suffix == ".py" else None
                    }
                    
                    perms = "r" if files_status["required"][file_path]["readable"] else "-"
                    perms += "w" if files_status["required"][file_path]["writable"] else "-"
                    if path.suffix == ".py":
                        perms += "x" if files_status["required"][file_path]["executable"] else "-"
                    
                    print(f"  ✅ {file_path}: {stat.st_size} байт, права: {perms}")
                    
                    if not files_status["required"][file_path]["readable"]:
                        files_status["permission_issues"].append(f"{file_path}: нет прав на чтение")
                    
                else:
                    files_status["missing_required"].append(file_path)
                    print(f"  ❌ {file_path}: НЕ НАЙДЕН!")
            
            print("\nДополнительные файлы и директории:")
            for file_path in optional_files:
                path = Path(file_path)
                if path.exists():
                    if path.is_dir():
                        files_count = len(list(path.glob("*")))
                        files_status["optional"][file_path] = {"exists": True, "type": "directory", "files_count": files_count}
                        print(f"  ✅ {file_path}: директория ({files_count} файлов)")
                    else:
                        stat = path.stat()
                        files_status["optional"][file_path] = {"exists": True, "type": "file", "size": stat.st_size}
                        print(f"  ✅ {file_path}: файл ({stat.st_size} байт)")
                else:
                    files_status["missing_optional"].append(file_path)
                    print(f"  ⚪ {file_path}: не найден")
            
            # Проверяем права на директории
            important_dirs = ["app/", "logs/"]
            for dir_path in important_dirs:
                path = Path(dir_path)
                if path.exists() and path.is_dir():
                    if not os.access(path, os.R_OK | os.W_OK):
                        files_status["permission_issues"].append(f"{dir_path}: недостаточно прав")
            
            self.results["files"] = files_status
            
            if files_status["missing_required"]:
                self.log_error(f"Отсутствуют критически важные файлы: {', '.join(files_status['missing_required'])}")
            
            if files_status["permission_issues"]:
                self.log_error(f"Проблемы с правами доступа: {', '.join(files_status['permission_issues'])}")
            
            if not files_status["missing_required"] and not files_status["permission_issues"]:
                self.log_success("Все файлы на месте с корректными правами доступа")
                
        except Exception as e:
            self.log_error("Ошибка проверки файлов", e)

    async def check_api_connectivity(self):
        """6. Проверка подключения к внешним API"""
        print("\n🌐 6. ПОДКЛЮЧЕНИЕ К ВНЕШНИМ API")
        print("=" * 50)
        
        api_tests = []
        
        # Telegram Bot API
        bot_token = os.getenv("BOT_TOKEN")
        if bot_token:
            api_tests.append({
                "name": "Telegram Bot API",
                "url": f"https://api.telegram.org/bot{bot_token}/getMe",
                "method": "GET",
                "expected_status": 200
            })
        
        # Pyrus API
        pyrus_url = os.getenv("PYRUS_API_URL", "https://api.pyrus.com/v4/")
        if pyrus_url:
            api_tests.append({
                "name": "Pyrus API",
                "url": f"{pyrus_url.rstrip('/')}/auth",
                "method": "POST",
                "data": {
                    "login": os.getenv("PYRUS_LOGIN", "test@example.com"),
                    "security_key": os.getenv("PYRUS_SECURITY_KEY", "dummy")
                },
                "expected_status": [200, 400, 401]  # 400/401 ожидаемы при неверных данных
            })
        
        # Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        if supabase_url:
            api_tests.append({
                "name": "Supabase API",
                "url": f"{supabase_url.rstrip('/')}/rest/v1/",
                "method": "GET",
                "headers": {
                    "apikey": os.getenv("SUPABASE_KEY", "dummy"),
                    "Authorization": f"Bearer {os.getenv('SUPABASE_KEY', 'dummy')}"
                },
                "expected_status": [200, 401, 403]  # 401/403 ожидаемы при неверном ключе
            })
        
        connectivity_results = {}
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                for test in api_tests:
                    print(f"\nТестирование {test['name']}...")
                    
                    try:
                        if test["method"] == "GET":
                            response = await client.get(
                                test["url"],
                                headers=test.get("headers", {})
                            )
                        else:  # POST
                            response = await client.post(
                                test["url"],
                                json=test.get("data", {}),
                                headers=test.get("headers", {})
                            )
                        
                        status_ok = response.status_code in (test["expected_status"] if isinstance(test["expected_status"], list) else [test["expected_status"]])
                        
                        connectivity_results[test["name"]] = {
                            "success": status_ok,
                            "status_code": response.status_code,
                            "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else None,
                            "url": test["url"].replace(bot_token or "dummy", "***TOKEN***") if bot_token else test["url"]
                        }
                        
                        if status_ok:
                            print(f"  ✅ {test['name']}: HTTP {response.status_code} - Доступен")
                        else:
                            print(f"  ❌ {test['name']}: HTTP {response.status_code} - Неожиданный статус")
                            
                    except httpx.TimeoutException:
                        connectivity_results[test["name"]] = {"success": False, "error": "Таймаут"}
                        print(f"  ❌ {test['name']}: Таймаут подключения")
                        
                    except Exception as e:
                        connectivity_results[test["name"]] = {"success": False, "error": str(e)}
                        print(f"  ❌ {test['name']}: Ошибка - {str(e)}")
            
            self.results["api_connectivity"] = connectivity_results
            
            failed_apis = [name for name, result in connectivity_results.items() if not result["success"]]
            if failed_apis:
                self.log_error(f"Недоступны API: {', '.join(failed_apis)}")
            else:
                self.log_success("Все API доступны")
                
        except ImportError:
            self.log_error("httpx не установлен - невозможно проверить API")
        except Exception as e:
            self.log_error("Ошибка проверки API подключений", e)

    def check_imports(self):
        """7. Проверка импорта модулей проекта"""
        print("\n📥 7. ИМПОРТ МОДУЛЕЙ ПРОЕКТА")
        print("=" * 50)
        
        modules_to_test = [
            "dotenv",
            "fastapi",
            "uvicorn", 
            "telegram",
            "supabase",
            "httpx",
            "pandas",
            "openpyxl",
            "pytz",
            "pydantic",
            "aiofiles",
            "pytest"
        ]
        
        project_modules = [
            "app.api",
            "app.bot", 
            "app.worker",
            "app.db",
            "app.utils",
            "app.models",
            "app.pyrus_client"
        ]
        
        import_results = {
            "external_packages": {},
            "project_modules": {},
            "failed_external": [],
            "failed_project": []
        }
        
        print("Внешние пакеты:")
        for module in modules_to_test:
            try:
                imported_module = importlib.import_module(module)
                version = getattr(imported_module, "__version__", "неизвестно")
                import_results["external_packages"][module] = {"success": True, "version": version}
                print(f"  ✅ {module}: версия {version}")
            except ImportError as e:
                import_results["external_packages"][module] = {"success": False, "error": str(e)}
                import_results["failed_external"].append(module)
                print(f"  ❌ {module}: Ошибка импорта - {str(e)}")
            except Exception as e:
                import_results["external_packages"][module] = {"success": False, "error": str(e)}
                import_results["failed_external"].append(module)
                print(f"  ❌ {module}: Неожиданная ошибка - {str(e)}")
        
        print("\nМодули проекта:")
        for module in project_modules:
            try:
                imported_module = importlib.import_module(module)
                import_results["project_modules"][module] = {"success": True}
                print(f"  ✅ {module}: импорт успешен")
            except ImportError as e:
                import_results["project_modules"][module] = {"success": False, "error": str(e)}
                import_results["failed_project"].append(module)
                print(f"  ❌ {module}: Ошибка импорта - {str(e)}")
            except Exception as e:
                import_results["project_modules"][module] = {"success": False, "error": str(e)}
                import_results["failed_project"].append(module)
                print(f"  ❌ {module}: Неожиданная ошибка - {str(e)}")
        
        self.results["imports"] = import_results
        
        total_failed = len(import_results["failed_external"]) + len(import_results["failed_project"])
        
        if import_results["failed_external"]:
            self.log_error(f"Не удалось импортировать внешние пакеты: {', '.join(import_results['failed_external'])}")
        
        if import_results["failed_project"]:
            self.log_error(f"Не удалось импортировать модули проекта: {', '.join(import_results['failed_project'])}")
        
        if total_failed == 0:
            self.log_success("Все модули импортируются без ошибок")

    async def check_database_connection(self):
        """8. Проверка подключения к базе данных"""
        print("\n🗄️  8. ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ")
        print("=" * 50)
        
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                self.log_error("SUPABASE_URL или SUPABASE_KEY не настроены")
                return
            
            # Пытаемся подключиться через наш модуль db
            try:
                from app.db import db
                
                # Тестируем простой запрос
                result = db.client.table("users").select("count", count="exact").limit(0).execute()
                
                db_status = {
                    "connection": True,
                    "url": supabase_url,
                    "tables_accessible": True
                }
                
                print(f"✅ Подключение к Supabase: успешно")
                print(f"✅ Доступ к таблице users: успешно")
                
                # Проверяем другие таблицы
                tables_to_check = ["pending_notifications"]
                for table in tables_to_check:
                    try:
                        db.client.table(table).select("count", count="exact").limit(0).execute()
                        print(f"✅ Доступ к таблице {table}: успешно")
                    except Exception as e:
                        print(f"⚠️ Таблица {table}: проблема доступа - {str(e)}")
                        db_status[f"table_{table}"] = False
                
                self.results["database"] = db_status
                self.log_success("База данных доступна и функциональна")
                
            except ImportError:
                self.log_error("Не удалось импортировать модуль app.db")
            except Exception as e:
                print(f"❌ Ошибка подключения к базе данных: {str(e)}")
                self.results["database"] = {"connection": False, "error": str(e)}
                self.log_error("Ошибка подключения к базе данных", e)
                
        except Exception as e:
            self.log_error("Ошибка проверки базы данных", e)

    def check_logs_and_system(self):
        """9. Проверка логов и системных ресурсов"""
        print("\n📋 9. ЛОГИ И СИСТЕМНЫЕ РЕСУРСЫ")
        print("=" * 50)
        
        logs_info = {
            "logs_directory": {},
            "system_logs": {},
            "disk_space": {},
            "memory": {}
        }
        
        try:
            # Проверяем папку логов проекта
            logs_dir = Path("logs")
            if logs_dir.exists():
                log_files = list(logs_dir.glob("*.log"))
                recent_logs = []
                
                for log_file in log_files:
                    stat = log_file.stat()
                    recent_logs.append({
                        "file": log_file.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                
                logs_info["logs_directory"] = {
                    "exists": True,
                    "files_count": len(log_files),
                    "recent_logs": recent_logs[:5]  # Показываем только 5 последних
                }
                
                print(f"✅ Директория logs: {len(log_files)} файлов")
                for log in recent_logs[:3]:
                    print(f"  📄 {log['file']}: {log['size']} байт (изменен {log['modified']})")
                    
            else:
                logs_info["logs_directory"] = {"exists": False}
                print("⚪ Директория logs не найдена")
            
            # Проверяем дисковое пространство
            disk_usage = self.run_command(["df", "-h", "."])
            if disk_usage["success"]:
                logs_info["disk_space"] = disk_usage["stdout"]
                print(f"💽 Дисковое пространство:\n{disk_usage['stdout']}")
            
            # Проверяем память
            if platform.system() == "Darwin":  # macOS
                memory_cmd = ["vm_stat"]
            else:  # Linux
                memory_cmd = ["free", "-h"]
            
            memory_info = self.run_command(memory_cmd)
            if memory_info["success"]:
                logs_info["memory"] = memory_info["stdout"]
                print(f"🧠 Память:\n{memory_info['stdout']}")
            
            # Проверяем загрузку системы
            if platform.system() != "Windows":
                load_avg = self.run_command(["uptime"])
                if load_avg["success"]:
                    logs_info["load_average"] = load_avg["stdout"]
                    print(f"📊 Загрузка системы: {load_avg['stdout']}")
            
            self.results["logs"] = logs_info
            self.log_success("Информация о логах и системе собрана")
            
        except Exception as e:
            self.log_error("Ошибка проверки логов и системы", e)

    def check_network_and_firewall(self):
        """10. Проверка сетевых настроек"""
        print("\n🌐 10. СЕТЕВЫЕ НАСТРОЙКИ")
        print("=" * 50)
        
        network_info = {}
        
        try:
            # Проверяем доступность интернета
            internet_test = self.run_command(["ping", "-c", "3", "8.8.8.8"])
            network_info["internet"] = {
                "available": internet_test["success"],
                "details": internet_test.get("stdout", internet_test.get("error", ""))
            }
            
            if internet_test["success"]:
                print("✅ Интернет соединение: доступно")
            else:
                print("❌ Интернет соединение: недоступно")
                self.log_error("Нет доступа к интернету")
            
            # Проверяем DNS
            dns_test = self.run_command(["nslookup", "api.telegram.org"])
            network_info["dns"] = {
                "working": dns_test["success"],
                "details": dns_test.get("stdout", dns_test.get("error", ""))
            }
            
            if dns_test["success"]:
                print("✅ DNS разрешение: работает")
            else:
                print("❌ DNS разрешение: проблемы")
                self.log_error("Проблемы с DNS")
            
            # Проверяем открытые порты (если запущен)
            port_check = self.run_command(["netstat", "-tuln"])
            if port_check["success"]:
                network_info["open_ports"] = port_check["stdout"]
                if ":8000" in port_check["stdout"]:
                    print("✅ Порт 8000: открыт (API сервер)")
                else:
                    print("⚪ Порт 8000: не используется")
            
            self.results["network"] = network_info
            
        except Exception as e:
            self.log_error("Ошибка проверки сети", e)

    def generate_recommendations(self):
        """Генерация рекомендаций на основе найденных проблем"""
        recommendations = []
        
        # Анализируем результаты и формируем рекомендации
        if self.results["environment"].get("missing_required"):
            missing = self.results["environment"]["missing_required"]
            recommendations.append(f"🔧 Настройте переменные окружения: {', '.join(missing)}")
        
        if self.results["packages"].get("missing"):
            missing = self.results["packages"]["missing"]
            recommendations.append(f"📦 Установите пакеты: pip install {' '.join(missing)}")
        
        if self.results["packages"].get("version_mismatch"):
            recommendations.append("📦 Обновите пакеты до требуемых версий: pip install -r requirements.txt --upgrade")
        
        if self.results["files"].get("missing_required"):
            missing = self.results["files"]["missing_required"]
            recommendations.append(f"📁 Восстановите отсутствующие файлы: {', '.join(missing)}")
        
        if self.results["files"].get("permission_issues"):
            recommendations.append("🔐 Исправьте права доступа к файлам: chmod -R 755 app/")
        
        if not self.results["python_info"].get("in_virtualenv"):
            recommendations.append("🐍 Создайте и активируйте виртуальное окружение")
        
        api_failures = [name for name, result in self.results["api_connectivity"].items() if not result["success"]]
        if api_failures:
            recommendations.append(f"🌐 Проверьте подключение к API: {', '.join(api_failures)}")
        
        if not self.results["database"].get("connection"):
            recommendations.append("🗄️ Проверьте настройки подключения к Supabase")
        
        if self.results["imports"].get("failed_external"):
            recommendations.append("📥 Переустановите проблемные пакеты")
        
        if self.results["imports"].get("failed_project"):
            recommendations.append("📥 Проверьте целостность файлов проекта")
        
        if not recommendations:
            recommendations.append("✅ Система настроена корректно! Возможно, проблема в других факторах.")
        
        self.results["recommendations"] = recommendations
        return recommendations

    async def run_full_diagnostics(self):
        """Запуск полной диагностики"""
        print("🔍 КОМПЛЕКСНАЯ ДИАГНОСТИКА PyrusTelegramBot")
        print("=" * 60)
        print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Рабочая директория: {Path.cwd()}")
        print("=" * 60)
        
        # Последовательно выполняем все проверки
        self.check_system_info()
        self.check_python_info()
        self.check_environment_variables()
        self.check_packages()
        self.check_files_and_permissions()
        await self.check_api_connectivity()
        self.check_imports()
        await self.check_database_connection()
        self.check_logs_and_system()
        self.check_network_and_firewall()
        
        # Генерируем рекомендации
        recommendations = self.generate_recommendations()
        
        # Выводим итоговый отчет
        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЙ ОТЧЕТ")
        print("=" * 60)
        
        print(f"\n❌ Ошибки: {len(self.results['errors'])}")
        for error in self.results["errors"]:
            print(f"  {error}")
        
        print(f"\n⚠️ Предупреждения: {len(self.results['warnings'])}")
        for warning in self.results["warnings"]:
            print(f"  {warning}")
        
        print(f"\n🔧 Рекомендации:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        # Сохраняем полный отчет в файл
        report_file = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n💾 Полный отчет сохранен в {report_file}")
        except Exception as e:
            print(f"\n❌ Ошибка сохранения отчета: {e}")
        
        print("\n" + "=" * 60)
        return self.results

async def main():
    """Главная функция"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
Диагностика PyrusTelegramBot
============================

Использование:
  python system_diagnostics.py [--help]

Скрипт проверяет:
1. Системную информацию
2. Python и виртуальное окружение  
3. Переменные окружения
4. Установленные пакеты
5. Файлы проекта и права доступа
6. Подключение к внешним API
7. Импорт модулей
8. Подключение к базе данных
9. Логи и системные ресурсы
10. Сетевые настройки

Результат сохраняется в JSON файл для сравнения между машинами.
        """)
        return
    
    diagnostics = SystemDiagnostics()
    await diagnostics.run_full_diagnostics()

if __name__ == "__main__":
    asyncio.run(main())

