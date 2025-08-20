import json
import os
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import asyncio
import aiofiles
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем наши модули
from .utils import verify_pyrus_signature, schedule_after
from .models import PyrusWebhookPayload
from .db import db

app = FastAPI(title="Pyrus Telegram Bot", version="1.0.0")

# Создаём папку для логов
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Загружаем конфигурацию из переменных окружения
PYRUS_WEBHOOK_SECRET = os.getenv("PYRUS_WEBHOOK_SECRET", "")
DEV_SKIP_PYRUS_SIG = os.getenv("DEV_SKIP_PYRUS_SIG", "false").lower() == "true"
DELAY_HOURS = float(os.getenv("DELAY_HOURS", "3"))
TZ = os.getenv("TZ", "Asia/Yekaterinburg")
QUIET_START = os.getenv("QUIET_START", "22:00")
QUIET_END = os.getenv("QUIET_END", "09:00")


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return PlainTextResponse("ok")


@app.post("/pyrus/webhook")
async def pyrus_webhook(request: Request):
    """
    Приём и обработка вебхуков от Pyrus
    
    Этап 3: реальная обработка упоминаний и реакций
    """
    # Считываем сырое тело запроса
    raw_body = await request.body()
    
    # Получаем заголовки
    headers = dict(request.headers)
    retry_header = headers.get("x-pyrus-retry", "1/1")
    signature_header = headers.get("x-pyrus-sig", "")
    
    try:
        # 1. Проверяем подпись HMAC
        if not verify_pyrus_signature(raw_body, PYRUS_WEBHOOK_SECRET, DEV_SKIP_PYRUS_SIG, signature_header):
            # Логируем в файл для отладки
            asyncio.create_task(_log_webhook_async(raw_body, retry_header, "invalid_signature"))
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # 2. Парсим JSON в модель
        try:
            payload_data = json.loads(raw_body.decode('utf-8'))
            payload = PyrusWebhookPayload(**payload_data)
        except (json.JSONDecodeError, Exception) as e:
            # Логируем ошибку парсинга
            asyncio.create_task(_log_webhook_async(raw_body, retry_header, f"parse_error: {e}"))
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        
        # 3. Обрабатываем событие (пока упрощенно)
        # В будущем здесь будет полная логика обработки
        
        # 4. Логируем успешную обработку  
        asyncio.create_task(_log_webhook_async(raw_body, retry_header, "processed"))
        
        return {"status": "ok", "message": "webhook processed"}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Логируем неожиданные ошибки
        asyncio.create_task(_log_webhook_async(raw_body, retry_header, f"error: {e}"))
        # Но всё равно возвращаем 200, чтобы Pyrus не ретраил
        print(f"Unexpected error processing webhook: {e}")
        return {"status": "error", "message": "Internal error, logged"}


async def _log_webhook_async(raw_body: bytes, retry_header: str, status: str = "unknown"):
    """Асинхронное логирование вебхука в файл"""
    try:
        # Формируем имя файла с датой
        today = datetime.now().strftime("%Y%m%d")
        log_file = LOGS_DIR / f"pyrus_raw_{today}.ndjson"
        
        # Пытаемся распарсить JSON
        try:
            payload = json.loads(raw_body.decode('utf-8'))
            is_valid_json = True
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"raw_body": raw_body.hex(), "error": "invalid_json"}
            is_valid_json = False
        
        # Создаём запись для лога
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "retry_header": retry_header,
            "status": status,
            "is_valid_json": is_valid_json,
            "payload": payload
        }
        
        # Записываем в файл (NDJSON формат)
        async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
            await f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
    except Exception as e:
        # Если что-то пошло не так, логируем в консоль
        print(f"Ошибка логирования вебхука: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 