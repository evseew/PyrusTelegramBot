import json
import os
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import asyncio
import aiofiles

app = FastAPI(title="Pyrus Telegram Bot", version="1.0.0")

# Создаём папку для логов
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return PlainTextResponse("ok")


@app.post("/pyrus/webhook")
async def pyrus_webhook(request: Request):
    """
    Приём вебхуков от Pyrus
    Пока просто логируем и отвечаем 200 OK
    """
    # Считываем сырое тело запроса
    raw_body = await request.body()
    
    # Получаем заголовки для логирования
    headers = dict(request.headers)
    retry_header = headers.get("x-pyrus-retry", "1/1")
    
    # Возвращаем 200 сразу, чтобы убрать ретраи от Pyrus
    response_task = asyncio.create_task(_log_webhook_async(raw_body, retry_header))
    
    return {"status": "ok", "message": "webhook received"}


async def _log_webhook_async(raw_body: bytes, retry_header: str):
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