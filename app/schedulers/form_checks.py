"""
Планировщик проверок формы 2304918:
- слот today21: target_day = сегодня
- слот yesterday12: target_day = вчера

Делает:
- читает метаданные формы (имя, поля)
- проходит реестр (только открытые)
- применяет правила и формирует сообщения
- адресует преподавателю по ФИО (фаззи-поиск) или админу
- ставит сообщения в существующий pending через db.log_event (для начала — только лог)

Важно: интеграцию с очередью pending для фактической отправки добавим отдельным шагом
после валидации сообщений (минимальный риск).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import pytz

from ..db import db
from ..pyrus_client import PyrusClient
from ..rules.form_2304918 import check_rules, TEACHER_ID
import os


def _tz_now(tz_name: str) -> datetime:
    return datetime.now(pytz.timezone(tz_name))


def _target_day_str(now_local: datetime, slot: str) -> str:
    if slot == "today21":
        d = now_local.date()
    else:
        d = (now_local - timedelta(days=1)).date()
    return d.isoformat()


def _build_fields_meta(form_meta: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for f in form_meta.get("fields", []) or []:
        fid = f.get("id")
        if isinstance(fid, int):
            out[fid] = {"name": f.get("name"), "type": f.get("type")}
    return out


def _extract_teacher_full_name(task_fields: List[Dict[str, Any]]) -> str:
    for f in task_fields:
        if f.get("id") == TEACHER_ID:
            v = f.get("value")
            if isinstance(v, dict):
                # попытаемся достать понятное имя
                # каталог/справочник может хранить как text/value/name
                return str(v.get("text") or v.get("value") or v.get("name") or "").strip()
            if isinstance(v, str):
                return v.strip()
    return ""


def _fuzzy_find_user_by_full_name(candidate: str, threshold: float = 0.85) -> Tuple[str, int] | Tuple[None, None]:
    """
    Возвращает (full_name, user_id) или (None, None) если нет точного 1 совпадения.
    Простейшая реализация: нормализованное сравнение по вхождению/ratio упрощённо.
    Для надёжности оставим требование строгого одного совпадения, иначе вернём None.
    """
    if not candidate:
        return (None, None)
    try:
        users = db.get_all_users()
        cand = candidate.lower().replace(" ", "")
        best = []
        for u in users:
            name = (u.full_name or "").lower().replace(" ", "")
            if not name:
                continue
            # простейший ratio: пересечение / максимум длины
            inter = len(set(cand) & set(name))
            denom = max(len(cand), len(name)) or 1
            ratio = inter / denom
            if ratio >= threshold:
                best.append((ratio, u.full_name, u.user_id))
        if len(best) == 1:
            _, full_name, user_id = best[0]
            return (full_name, user_id)
        else:
            return (None, None)
    except Exception:
        return (None, None)


def _format_today_message(task_title: str, task_id: int, errors: List[str]) -> str:
    lines = [f"Привет! В задаче «{task_title}» есть что поправить на сегодня:", ""]
    lines.extend([f"– {e}" for e in errors])
    lines.append("")
    lines.append(f"Ссылка на задачу: https://pyrus.com/t#id{task_id}")
    return "\n".join(lines)


def _format_noon_header(form_name: str) -> str:
    return f"Доброе утро! Небольшая сводка по вчерашним задачам формы «{form_name}»:\n"


async def run_slot(slot: str) -> None:
    """
    Выполнить проверку для указанного слота: "today21" или "yesterday12".
    Пока: складываем события в логи и фиксируем потенциальные адресаты.
    Следующим шагом подключим постановку в pending.
    """
    tz = os.getenv("TZ", "Asia/Yekaterinburg")
    form_id = int(os.getenv("FORM_ID", "2304918"))

    now_local = _tz_now(tz)
    target = _target_day_str(now_local, slot)

    client = PyrusClient()
    form_meta = await client.get_form_meta(form_id)
    if not form_meta:
        db.log_event("form_meta_error", {"slot": slot, "form_id": form_id})
        return

    fields_meta = _build_fields_meta(form_meta)
    form_name = form_meta.get("name") or f"Форма {form_id}"

    # Сбор найденных по преподавателям (для noon)
    per_teacher: Dict[int, List[Tuple[int, str]]] = {}
    ambiguous_to_admin: List[Tuple[str, int, List[str]]] = []
    fallback_to_admin: List[Tuple[str, int, List[str]]] = []

    async for t in client.iter_register_tasks(form_id, include_archived=False):
        task_id = t.get("id") or t.get("task_id")
        task_fields = t.get("fields") or []
        task_title = ""
        # title может храниться в поле id=1 (title) внутри fields
        for f in task_fields or []:
            if f.get("id") == 1:
                val = f.get("value") or {}
                # Берём реальное текстовое значение заголовка
                if isinstance(val, dict):
                    task_title = str(val.get("text") or val.get("value") or val.get("name") or f.get("name") or "Задача").strip()
                elif isinstance(val, str):
                    task_title = val.strip() or (f.get("name") or "Задача").strip()
                else:
                    task_title = (f.get("name") or "Задача").strip()
                break

        errors = check_rules(fields_meta, task_fields, target, slot)
        if not errors:
            continue

        # адресат: преподаватель по ФИО
        teacher_name = _extract_teacher_full_name(task_fields)
        full_name, user_id = _fuzzy_find_user_by_full_name(teacher_name, threshold=0.85)
        if full_name and user_id:
            # Кладём в агрегатор (позже разобьём на today/noon)
            per_teacher.setdefault(user_id, []).append((task_id, _format_today_message(task_title or "Задача", task_id, errors)))
        else:
            # Не нашли или неоднозначно — админу
            ambiguous_to_admin.append((teacher_name or "", task_id, errors))

    # Логируем, что нашли (на следующем шаге — постановка в pending)
    db.log_event("form_check_summary", {
        "slot": slot,
        "form_id": form_id,
        "form_name": form_name,
        "teachers_found": len(per_teacher),
        "ambiguous": len(ambiguous_to_admin),
    })
    print(f"[form_checks] slot={slot} form='{form_name}' teachers_found={len(per_teacher)} ambiguous={len(ambiguous_to_admin)}")

    # Постановка в очередь: для каждого пользователя создаём отдельные записи
    # today21 — по одной задаче = одно сообщение; yesterday12 — предварительно агрегировали бы,
    # но в рамках очереди кладём по одной записи на задачу, а воркер отправит последовательно.
    import hashlib
    # Читаем ADMIN_IDS напрямую из окружения, чтобы избежать импорта bot и сайд-эффектов
    admin_ids_env = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_env.split(",") if x.strip().isdigit()]
    import pytz

    tz = pytz.timezone(os.getenv("TZ", "Asia/Yekaterinburg"))
    send_at = _tz_now(os.getenv("TZ", "Asia/Yekaterinburg"))

    for user_id, msgs in per_teacher.items():
        for task_id, text in msgs:
            h = hashlib.sha256((slot + str(task_id) + str(user_id) + text).encode("utf-8")).hexdigest()
            try:
                db.enqueue_preformatted(
                    task_id=int(task_id),
                    user_id=int(user_id),
                    send_at=send_at.astimezone(pytz.UTC).replace(tzinfo=None),
                    slot=slot,
                    message_text=text,
                    dedupe_hash=h,
                )
            except Exception as e:
                db.log_event("enqueue_error", {"user_id": user_id, "task_id": task_id, "error": str(e)})

    # Фолбэк админу
    admin_ids = ADMIN_IDS or []
    for teacher_name, task_id, errors in ambiguous_to_admin:
        if not admin_ids:
            continue
        text = _format_today_message(f"Задача #{task_id}", int(task_id), errors)
        text = f"Админ, нужна помощь: не нашёл/несколько совпадений для преподавателя «{teacher_name}».\n\n" + text
        h = hashlib.sha256((slot + str(task_id) + "admin" + teacher_name + "|".join(errors)).encode("utf-8")).hexdigest()
        try:
            db.enqueue_preformatted(
                task_id=int(task_id),
                user_id=int(admin_ids[0]),
                send_at=send_at.astimezone(pytz.UTC).replace(tzinfo=None),
                slot=slot,
                message_text=text,
                dedupe_hash=h,
            )
        except Exception as e:
            db.log_event("enqueue_admin_error", {"task_id": task_id, "error": str(e)})


