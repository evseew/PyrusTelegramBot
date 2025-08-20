"""
Модели данных для валидации Pyrus webhook payload
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class PyrusUser(BaseModel):
    """Пользователь Pyrus"""
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    # Другие поля добавим по мере необходимости


class PyrusComment(BaseModel):
    """Комментарий в задаче Pyrus"""
    id: int
    text: str
    create_date: datetime
    author: PyrusUser
    mentions: List[int] = Field(default_factory=list)  # user_id упомянутых


class PyrusTask(BaseModel):
    """Задача Pyrus"""
    id: int
    subject: Optional[str] = None
    comments: List[PyrusComment] = Field(default_factory=list)
    # Добавим другие поля по мере изучения реальных webhook


class PyrusWebhookPayload(BaseModel):
    """Основная структура webhook от Pyrus"""
    event: str  # "comment", "task_updated", "task_closed", etc.
    task: PyrusTask
    actor: Optional[PyrusUser] = None
    change: Optional[Dict[str, Any]] = None
    # Другие поля добавим по мере изучения


class PendingNotification(BaseModel):
    """Запись в очереди уведомлений"""
    task_id: int
    user_id: int
    first_mention_at: datetime
    last_mention_at: datetime
    last_mention_comment_id: Optional[int] = None
    last_mention_comment_text: Optional[str] = None
    next_send_at: datetime
    times_sent: int = 0


class User(BaseModel):
    """Зарегистрированный пользователь"""
    user_id: int
    telegram_id: int
    phone: Optional[str] = None
    full_name: Optional[str] = None
    updated_at: Optional[datetime] = None
