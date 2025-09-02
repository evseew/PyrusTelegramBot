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
from ..rules.form_2304918 import check_rules, TEACHER_ID, _get_field_value
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
    """Надёжно достать ФИО преподавателя из поля TEACHER_ID, учитывая вложенные секции.

    Используем рекурсивный поиск значения из rules._get_field_value, затем извлекаем текст.
    """
    v = _get_field_value(task_fields, TEACHER_ID)
    if isinstance(v, dict):
        return str(v.get("text") or v.get("value") or v.get("name") or "").strip()
    if isinstance(v, str):
        return v.strip()
    return ""


def _extract_teacher_user_id(task_fields: List[Dict[str, Any]]) -> int | None:
    """Попробовать достать Pyrus user_id из поля TEACHER_ID.

    Поддерживаем варианты:
    - dict с ключами id / user_id / value (int или str-число)
    - прямое значение int/str в поле
    """
    v = _get_field_value(task_fields, TEACHER_ID)
    if isinstance(v, dict):
        for k in ("id", "user_id", "value"):
            val = v.get(k)
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return None


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
    """Дружелюбное сообщение для преподавателя с эмоджи и ограничением длины заголовка."""
    import os as _os
    limit = int(_os.getenv("TRUNC_TASK_TITLE_LEN", "50"))
    title_short = (task_title or "Задача")[:limit]

    bullet = "•"  # компактная марка списка
    lines = [
        f"👋 Привет! В задаче «{title_short}» сегодня есть небольшие дела:",
        "",
    ]
    lines.extend([f"{bullet} {e}" for e in errors])
    lines.append("")
    lines.append(f"🔗 Ссылка: https://pyrus.com/t#id{task_id}")
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

        # адресат: приоритетно — по Pyrus user_id из поля, иначе — по ФИО (фаззи)
        teacher_user_id = _extract_teacher_user_id(task_fields)
        if isinstance(teacher_user_id, int):
            per_teacher.setdefault(teacher_user_id, []).append((task_id, _format_today_message(task_title or "Задача", task_id, errors)))
        else:
            teacher_name = _extract_teacher_full_name(task_fields)
            full_name, user_id = _fuzzy_find_user_by_full_name(teacher_name, threshold=0.85)
            if full_name and user_id:
                per_teacher.setdefault(user_id, []).append((task_id, _format_today_message(task_title or "Задача", task_id, errors)))
            else:
                # Не нашли или неоднозначно — в сводку админу (без индивидуальных рассылок)
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

    # Фолбэк: один агрегированный отчёт админу вместо множества сообщений
    admin_ids = ADMIN_IDS or []
    if admin_ids:
        # Подсчёты
        sent_forms = sum(len(msgs) for msgs in per_teacher.values())
        sent_teachers = len(per_teacher)
        not_sent_forms = len(ambiguous_to_admin)
        unknown_teachers = len({(name or "").strip() for name, _, _ in ambiguous_to_admin if (name or "").strip()})

        # Формируем текст отчёта
        report_lines = [
            f"Админ-отчёт по форме «{form_name}» за {target} (слот {slot})",
            "",
            f"Разослано: {sent_forms} задач, преподавателей: {sent_teachers}",
            f"Не разослано: {not_sent_forms} задач",
            f"Преподавателей не найдено в системе: {unknown_teachers}",
        ]
        report_text = "\n".join(report_lines)

        # Отдельный слот для отчётов, чтобы воркер применил специальную доставку
        report_slot = f"report_{slot}"
        import hashlib as _hashlib
        report_hash = _hashlib.sha256((report_slot + target + str(sent_forms) + str(not_sent_forms) + str(unknown_teachers)).encode("utf-8")).hexdigest()

        try:
            db.enqueue_preformatted(
                task_id=0,  # служебный отчёт, не привязан к задаче
                user_id=int(admin_ids[0]),  # TG chat_id
                send_at=send_at.astimezone(pytz.UTC).replace(tzinfo=None),
                slot=report_slot,
                message_text=report_text,
                dedupe_hash=report_hash,
            )
        except Exception as e:
            db.log_event("enqueue_admin_report_error", {"error": str(e), "slot": report_slot})


