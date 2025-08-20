#!/usr/bin/env python3
"""
Основной скрипт для запуска всех компонентов Этапа 5
Может запускать API, Telegram бота и воркер в разных комбинациях
"""
import asyncio
import argparse
import os
import signal
import sys
from typing import List
import subprocess
from pathlib import Path


async def run_api():
    """Запуск FastAPI сервера"""
    print("🚀 Запуск API сервера...")
    process = await asyncio.create_subprocess_exec(
        "uvicorn", "app.api:app", 
        "--host", "0.0.0.0", 
        "--port", "8000", 
        "--reload"
    )
    return process


async def run_bot():
    """Запуск Telegram бота"""
    print("🤖 Запуск Telegram бота...")
    process = await asyncio.create_subprocess_exec(
        "python", "-m", "app.bot"
    )
    return process


async def run_worker():
    """Запуск фонового воркера"""
    print("⚙️ Запуск фонового воркера...")
    process = await asyncio.create_subprocess_exec(
        "python", "-m", "app.worker"
    )
    return process


async def run_all():
    """Запуск всех компонентов"""
    print("🚀 Запуск всех компонентов Этапа 5...")
    print("=" * 60)
    
    # Запускаем все процессы
    api_process = await run_api()
    bot_process = await run_bot()
    worker_process = await run_worker()
    
    processes = [api_process, bot_process, worker_process]
    
    print("\n✅ Все компоненты запущены!")
    print("📡 API: http://localhost:8000")
    print("🤖 Telegram бот активен")
    print("⚙️ Воркер обрабатывает очередь")
    print("\nДля остановки нажмите Ctrl+C")
    print("=" * 60)
    
    try:
        # Ждём завершения любого процесса
        done, pending = await asyncio.wait(
            [asyncio.create_task(p.wait()) for p in processes],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Если один процесс завершился, останавливаем остальные
        for task in pending:
            task.cancel()
        
        for process in processes:
            if process.returncode is None:
                process.terminate()
                await process.wait()
                
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки...")
        
        for process in processes:
            if process.returncode is None:
                process.terminate()
                await process.wait()
        
        print("✅ Все процессы остановлены")


def check_environment():
    """Проверка окружения перед запуском"""
    print("🔍 Проверка окружения...")
    
    # Проверяем обязательные переменные
    required_vars = [
        "SUPABASE_URL", "SUPABASE_KEY", 
        "PYRUS_WEBHOOK_SECRET", "PYRUS_LOGIN", "PYRUS_SECURITY_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("📝 Проверьте файл .env")
        return False
    
    # Проверяем BOT_TOKEN для Telegram
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("⚠️ BOT_TOKEN не установлен - воркер будет в DRY_RUN режиме")
    else:
        print("✅ BOT_TOKEN найден - реальная отправка уведомлений")
    
    # Проверяем файлы
    required_files = [
        "app/api.py", "app/bot.py", "app/worker.py", 
        "app/db.py", "app/utils.py", "app/models.py"
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Отсутствует файл: {file_path}")
            return False
    
    print("✅ Все проверки пройдены")
    return True


def main():
    parser = argparse.ArgumentParser(description="Запуск компонентов Pyrus Telegram Bot")
    parser.add_argument("--component", 
                       choices=["api", "bot", "worker", "all"], 
                       default="all",
                       help="Какой компонент запустить")
    parser.add_argument("--no-check", action="store_true", 
                       help="Пропустить проверку окружения")
    
    args = parser.parse_args()
    
    # Проверяем окружение
    if not args.no_check and not check_environment():
        sys.exit(1)
    
    # Запускаем выбранный компонент
    if args.component == "api":
        os.execvp("uvicorn", ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
    elif args.component == "bot":
        os.execvp("python", ["python", "-m", "app.bot"])
    elif args.component == "worker":
        os.execvp("python", ["python", "-m", "app.worker"])
    elif args.component == "all":
        asyncio.run(run_all())


if __name__ == "__main__":
    main()
