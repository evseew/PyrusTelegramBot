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
        
        # 3. Обрабатываем событие по типу
        await _process_webhook_event(payload, retry_header)
        
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


async def _process_webhook_event(payload: PyrusWebhookPayload, retry_header: str):
    """
    Обработка события вебхука согласно PRD
    
    Args:
        payload: Распарсенный webhook payload
        retry_header: Заголовок повтора
    """
    try:
        event_type = payload.event
        task = payload.task
        task_id = task.id
        actor = payload.actor
        
        # Логируем событие
        db.log_event("webhook_received", {
            "event": event_type,
            "task_id": task_id,
            "actor_id": actor.id if actor else None,
            "retry_header": retry_header
        })
        
        if event_type == "comment":
            await _handle_comment_event(task, retry_header)
        elif event_type in ["task_updated", "form_updated"]:
            await _handle_task_update_event(task, actor, payload.change)
        elif event_type in ["task_closed", "task_canceled"]:
            await _handle_task_closed_event(task_id)
        elif event_type == "comment_deleted":
            await _handle_comment_deleted_event(task, payload.change)
        else:
            print(f"⚠️ Неизвестный тип события: {event_type}")
            
    except Exception as e:
        print(f"❌ Ошибка обработки вебхука: {e}")
        db.log_event("webhook_error", {
            "error": str(e),
            "event": payload.event if payload else "unknown",
            "task_id": payload.task.id if payload and payload.task else None
        })


async def _handle_comment_event(task, retry_header: str):
    """Обработка события комментария с упоминаниями"""
    if not task.comments:
        return
    
    # Берём последний комментарий
    latest_comment = max(task.comments, key=lambda c: c.create_date)
    
    # Проверяем идемпотентность
    if db.processed_comment_exists(task.id, latest_comment.id):
        print(f"🔄 Комментарий {latest_comment.id} уже обработан (повтор)")
        return
    
    # Отмечаем как обработанный
    db.insert_processed_comment(task.id, latest_comment.id)
    
    # Обрабатываем упоминания
    if latest_comment.mentions:
        print(f"👥 Найдено {len(latest_comment.mentions)} упоминаний в задаче {task.id}")
        
        for user_id in latest_comment.mentions:
            # Проверяем, зарегистрирован ли пользователь
            user = db.get_user(user_id)
            if not user:
                print(f"⚠️ Пользователь {user_id} не зарегистрирован, пропускаем")
                continue
            
            # Планируем уведомление
            mention_time = latest_comment.create_date
            next_send_at = schedule_after(mention_time, DELAY_HOURS, TZ, QUIET_START, QUIET_END)
            
            db.upsert_or_shift_pending(
                task_id=task.id,
                user_id=user_id,
                mention_ts=mention_time,
                comment_id=latest_comment.id,
                comment_text=latest_comment.text,
                next_send_at=next_send_at
            )
            
            db.log_event("mention_queued", {
                "task_id": task.id,
                "user_id": user_id,
                "comment_id": latest_comment.id,
                "next_send_at": next_send_at.isoformat()
            })
            
            print(f"📬 Запланировано уведомление для пользователя {user_id} на {next_send_at.strftime('%d.%m %H:%M')}")


async def _handle_task_update_event(task, actor, change):
    """Обработка обновления задачи (реакция пользователя)"""
    if not actor:
        return
    
    # Это реакция пользователя - удаляем его из очереди
    db.delete_pending(task.id, actor.id)
    
    db.log_event("user_reacted", {
        "task_id": task.id,
        "user_id": actor.id,
        "change_type": change.get("kind") if change else "unknown"
    })
    
    print(f"✅ Пользователь {actor.id} отреагировал на задачу {task.id}, удалили из очереди")


async def _handle_task_closed_event(task_id: int):
    """Обработка закрытия/отмены задачи"""
    db.delete_pending_by_task(task_id)
    
    db.log_event("task_closed", {
        "task_id": task_id
    })
    
    print(f"🔒 Задача {task_id} закрыта, очистили всю очередь по этой задаче")


async def _handle_comment_deleted_event(task, change):
    """Обработка удаления/редактирования комментария"""
    if not change or "comment_id" not in change:
        return
    
    comment_id = change["comment_id"]
    
    # Находим записи в очереди с этим комментарием
    # В упрощённой версии удаляем все записи по задаче
    # В полной версии нужно будет проверять last_mention_comment_id
    
    db.log_event("comment_deleted", {
        "task_id": task.id,
        "comment_id": comment_id
    })
    
    print(f"🗑️ Комментарий {comment_id} удален/изменён в задаче {task.id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 