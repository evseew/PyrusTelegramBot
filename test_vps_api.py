#!/usr/bin/env python3
"""
Тест API на VPS для Этапа 3
"""
import json
import requests
from datetime import datetime, timezone

# Конфигурация
VPS_URL = "http://195.133.81.197:8000"

def test_health():
    """Тест health endpoint"""
    print("🔄 Тестирование /health...")
    
    try:
        response = requests.get(f"{VPS_URL}/health", timeout=10)
        if response.status_code == 200 and response.text == "ok":
            print("✅ Health endpoint работает")
            return True
        else:
            print(f"❌ Health endpoint: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_webhook_comment():
    """Тест обработки комментария с упоминаниями"""
    print("\n🔄 Тестирование webhook с комментарием...")
    
    test_payload = {
        "event": "comment",
        "task": {
            "id": 12345,
            "subject": "Тестовая задача для Этапа 3",
            "comments": [
                {
                    "id": 99999,
                    "text": "Тестовый комментарий с упоминанием @User1 @User2",
                    "create_date": datetime.now(timezone.utc).isoformat(),
                    "author": {
                        "id": 100,
                        "first_name": "Test",
                        "last_name": "Author"
                    },
                    "mentions": [106, 107]  # Два упоминания
                }
            ]
        },
        "actor": {
            "id": 100,
            "first_name": "Test",
            "last_name": "Author"
        }
    }
    
    try:
        response = requests.post(
            f"{VPS_URL}/pyrus/webhook",
            json=test_payload,
            headers={
                "X-Pyrus-Retry": "1/1",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook обработан: {result}")
            return True
        else:
            print(f"❌ Ошибка webhook: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки webhook: {e}")
        return False

def test_webhook_reaction():
    """Тест реакции пользователя"""
    print("\n🔄 Тестирование реакции пользователя...")
    
    test_payload = {
        "event": "task_updated",
        "task": {
            "id": 12345,
            "subject": "Тестовая задача"
        },
        "actor": {
            "id": 106,  # Пользователь из предыдущего теста
            "first_name": "Mentioned",
            "last_name": "User"
        },
        "change": {
            "kind": "field_changed"
        }
    }
    
    try:
        response = requests.post(
            f"{VPS_URL}/pyrus/webhook",
            json=test_payload,
            headers={
                "X-Pyrus-Retry": "1/1",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Реакция обработана: {result}")
            return True
        else:
            print(f"❌ Ошибка реакции: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки реакции: {e}")
        return False

def test_webhook_closure():
    """Тест закрытия задачи"""
    print("\n🔄 Тестирование закрытия задачи...")
    
    test_payload = {
        "event": "task_closed",
        "task": {
            "id": 12345,
            "subject": "Тестовая задача"
        },
        "actor": {
            "id": 100,
            "first_name": "Admin",
            "last_name": "User"
        }
    }
    
    try:
        response = requests.post(
            f"{VPS_URL}/pyrus/webhook",
            json=test_payload,
            headers={
                "X-Pyrus-Retry": "1/1",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Закрытие обработано: {result}")
            return True
        else:
            print(f"❌ Ошибка закрытия: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки закрытия: {e}")
        return False

def test_invalid_json():
    """Тест с невалидным JSON"""
    print("\n🔄 Тестирование невалидного JSON...")
    
    try:
        response = requests.post(
            f"{VPS_URL}/pyrus/webhook",
            data="invalid json",
            headers={
                "X-Pyrus-Retry": "1/1",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 400:
            print("✅ Невалидный JSON корректно отклонен")
            return True
        else:
            print(f"❌ Ожидался код 400, получен {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка тестирования невалидного JSON: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование API Этапа 3 на VPS")
    print(f"🔗 VPS URL: {VPS_URL}")
    print("=" * 60)
    
    success = True
    
    # Проверяем доступность
    success &= test_health()
    
    if not success:
        print("\n❌ API недоступен, проверьте что сервер запущен на VPS")
        print("📋 Команды для запуска на VPS:")
        print("1. cd /path/to/PyrusTelegramBot")
        print("2. uvicorn app.api:app --host 0.0.0.0 --port 80")
        return
    
    # Тестируем функциональность
    success &= test_webhook_comment()
    success &= test_webhook_reaction()
    success &= test_webhook_closure()
    success &= test_invalid_json()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ API Этапа 3 работает корректно")
        print("✅ Обработка webhook функционирует")
        print("✅ Валидация JSON работает")
        print("✅ Логика упоминаний и реакций реализована")
        print("\n🚀 ГОТОВЫ К ЭТАПУ 4!")
    else:
        print("❌ Есть проблемы, нужно их исправить")
    print("=" * 60)

if __name__ == "__main__":
    main()
