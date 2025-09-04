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
from ..rules.form_2304918 import check_rules, TEACHER_ID, TEACHER_RULE3_ID, _get_field_value


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


def _extract_teacher_full_name(task_fields: List[Dict[str, Any]], field_id: int = TEACHER_ID) -> str:
    """Надёжно достать ФИО преподавателя из поля TEACHER_ID, учитывая вложенные секции.

    Используем рекурсивный поиск значения из rules._get_field_value, затем извлекаем текст.
    """
    v = _get_field_value(task_fields, field_id)
    if isinstance(v, dict):
        return str(v.get("text") or v.get("value") or v.get("name") or "").strip()
    if isinstance(v, str):
        return v.strip()
    return ""


def _extract_teacher_user_id(task_fields: List[Dict[str, Any]], field_id: int = TEACHER_ID) -> int | None:
    """Попробовать достать Pyrus user_id из поля TEACHER_ID.

    Поддерживаем варианты:
    - dict с ключами id / user_id / value (int или str-число)
    - прямое значение int/str в поле
    """
    v = _get_field_value(task_fields, field_id)
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
    for i, e in enumerate(errors):
        lines.append(f"{bullet} {e}")
        if i != len(errors) - 1:
            lines.append("")
    lines.append("")
    lines.append(f"🔗 Ссылка: https://pyrus.com/t#id{task_id}")
    return "\n".join(lines)


def _format_yesterday_message(task_title: str, task_id: int, errors: List[str]) -> str:
    """Сообщение для сводки за вчера (слот yesterday12)."""
    import os as _os
    limit = int(_os.getenv("TRUNC_TASK_TITLE_LEN", "50"))
    title_short = (task_title or "Задача")[:limit]

    bullet = "•"
    lines = [
        f"👋 Привет! В задаче «{title_short}» вчера были небольшие дела:",
        "",
    ]
    for i, e in enumerate(errors):
        lines.append(f"{bullet} {e}")
        if i != len(errors) - 1:
            lines.append("")
    lines.append("")
    lines.append(f"🔗 Ссылка: https://pyrus.com/t#id{task_id}")
    return "\n".join(lines)


def _format_noon_header(form_name: str) -> str:
    return f"Доброе утро! Небольшая сводка по вчерашним задачам формы «{form_name}»:\n"


async def run_slot(slot: str) -> None:
    """
    Выполнить проверку для указанного слота: "today21" или "yesterday12".
    Поддерживает множественные формы из FORM_ID=2304918,792300
    """
    # Проверяем, нужно ли использовать множественные формы
    form_ids_str = os.getenv("FORM_ID", "2304918")
    if "," in form_ids_str:
        # Обрабатываем множественные формы
        await run_slot_multi(slot)
        return
    
    # Старая логика для одной формы
    tz = os.getenv("TZ", "Asia/Yekaterinburg")
    form_id = int(form_ids_str.strip())

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

    async for t in client.iter_register_tasks(form_id, include_archived=False):
        task_id = t.get("id") or t.get("task_id")
        task_fields = t.get("fields") or []
        # Сначала пытаемся взять заголовок как при обработке упоминаний: subject → text
        task_title = (t.get("subject") or t.get("text") or "").strip()
        # Фолбэк: поле id=1 (title) в fields, если subject/text пусты
        if not task_title:
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

        errors_map = check_rules(fields_meta, task_fields, target, slot)
        general_errors = errors_map.get("general") or []
        rule3_errors = errors_map.get("rule3") or []
        if not general_errors and not rule3_errors:
            continue

        _fmt = _format_today_message if slot == "today21" else _format_yesterday_message

        # 1) Общие ошибки → основной преподаватель (TEACHER_ID)
        if general_errors:
            teacher_user_id = _extract_teacher_user_id(task_fields, TEACHER_ID)
            if isinstance(teacher_user_id, int):
                try:
                    user_obj = db.get_user(int(teacher_user_id))
                except Exception:
                    user_obj = None
                if user_obj:
                    per_teacher.setdefault(teacher_user_id, []).append((task_id, _fmt(task_title or "Задача", task_id, general_errors)))
                else:
                    teacher_name = _extract_teacher_full_name(task_fields, TEACHER_ID)
                    ambiguous_to_admin.append((teacher_name or "", task_id, general_errors))
            else:
                teacher_name = _extract_teacher_full_name(task_fields, TEACHER_ID)
                full_name, user_id = _fuzzy_find_user_by_full_name(teacher_name, threshold=0.85)
                if full_name and user_id:
                    per_teacher.setdefault(user_id, []).append((task_id, _fmt(task_title or "Задача", task_id, general_errors)))
                else:
                    ambiguous_to_admin.append((teacher_name or "", task_id, general_errors))

        # 2) Ошибки правила 3 → преподаватель из поля 49 (TEACHER_RULE3_ID)
        if rule3_errors:
            teacher_user_id_r3 = _extract_teacher_user_id(task_fields, TEACHER_RULE3_ID)
            if isinstance(teacher_user_id_r3, int):
                try:
                    user_obj_r3 = db.get_user(int(teacher_user_id_r3))
                except Exception:
                    user_obj_r3 = None
                if user_obj_r3:
                    per_teacher.setdefault(teacher_user_id_r3, []).append((task_id, _fmt(task_title or "Задача", task_id, rule3_errors)))
                else:
                    teacher_name_r3 = _extract_teacher_full_name(task_fields, TEACHER_RULE3_ID)
                    ambiguous_to_admin.append((teacher_name_r3 or "", task_id, rule3_errors))
            else:
                teacher_name_r3 = _extract_teacher_full_name(task_fields, TEACHER_RULE3_ID)
                full_name_r3, user_id_r3 = _fuzzy_find_user_by_full_name(teacher_name_r3, threshold=0.85)
                if full_name_r3 and user_id_r3:
                    per_teacher.setdefault(user_id_r3, []).append((task_id, _fmt(task_title or "Задача", task_id, rule3_errors)))
                else:
                    ambiguous_to_admin.append((teacher_name_r3 or "", task_id, rule3_errors))

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
    send_at = _tz_now(tz.zone)

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
        # ВАЖНО: колонка slot в БД имеет ограничение varchar(16), поэтому используем короткие коды
        # today21 -> report_t21, yesterday12 -> report_y12
        short = {"today21": "t21", "yesterday12": "y12"}.get(slot, (slot or "")[:8])
        report_slot = f"report_{short}"
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


async def run_slot_multi(slot: str) -> None:
    """
    Выполнить проверку для множественных форм из FORM_ID.
    """
    tz = os.getenv("TZ", "Asia/Yekaterinburg")
    form_ids_str = os.getenv("FORM_ID", "2304918")
    
    # Парсим список форм
    form_ids = []
    for fid_str in form_ids_str.split(","):
        try:
            form_ids.append(int(fid_str.strip()))
        except ValueError:
            continue
    
    if not form_ids:
        print(f"⚠️ Нет валидных form_id в FORM_ID={form_ids_str}")
        db.log_event("form_ids_empty", {"slot": slot, "form_ids_str": form_ids_str})
        return

    now_local = _tz_now(tz)
    target = _target_day_str(now_local, slot)
    
    # Читаем ADMIN_IDS
    admin_ids_env = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_env.split(",") if x.strip().isdigit()]
    
    client = PyrusClient()
    
    # Обрабатываем каждую форму
    total_sent_forms = 0
    total_sent_teachers = 0
    total_not_sent = 0
    total_unknown = 0
    form_reports = []  # Отчеты по каждой форме
    
    for form_id in form_ids:
        try:
            # Выбираем правила для формы
            if form_id == 2304918:
                from ..rules.form_2304918 import check_rules, TEACHER_ID, TEACHER_RULE3_ID, _get_field_value
                use_fuzzy_search = True
            elif form_id == 792300:
                from ..rules.form_792300 import check_rules, TEACHER_ID, _get_field_value, _extract_teacher_full_name, _extract_teacher_user_id
                TEACHER_RULE3_ID = None  # У формы 792300 нет отдельного поля для правила 3
                use_fuzzy_search = False  # Используем прямое соответствие
            else:
                db.log_event("unsupported_form", {"slot": slot, "form_id": form_id})
                continue
            
            form_meta = await client.get_form_meta(form_id)
            if not form_meta:
                db.log_event("form_meta_error", {"slot": slot, "form_id": form_id})
                continue

            fields_meta = _build_fields_meta(form_meta)
            form_name = form_meta.get("name") or f"Форма {form_id}"
            
            per_teacher: Dict[int, List[Tuple[int, str]]] = {}
            ambiguous_to_admin: List[Tuple[str, int, List[str]]] = []
            
            # Проверяем задачи формы
            async for t in client.iter_register_tasks(form_id, include_archived=False):
                task_id = t.get("id") or t.get("task_id")
                task_fields = t.get("fields") or []
                task_title = (t.get("subject") or t.get("text") or f"Задача #{task_id}").strip()
                
                # Если заголовок пустой, берем из поля id=1
                if not task_title:
                    for f in task_fields or []:
                        if f.get("id") == 1:
                            val = f.get("value") or {}
                            if isinstance(val, dict):
                                task_title = str(val.get("text") or val.get("value") or val.get("name") or f.get("name") or "Задача").strip()
                            elif isinstance(val, str):
                                task_title = val.strip() or (f.get("name") or "Задача").strip()
                            else:
                                task_title = (f.get("name") or "Задача").strip()
                            break
                
                errors_map = check_rules(fields_meta, task_fields, target, slot)
                general_errors = errors_map.get("general") or []
                rule3_errors = errors_map.get("rule3") or []
                
                if not general_errors and not rule3_errors:
                    continue

                _fmt = _format_today_message if slot == "today21" else _format_yesterday_message

                # 1) Общие ошибки → преподаватель
                if general_errors:
                    teacher_user_id = _extract_teacher_user_id(task_fields, TEACHER_ID)
                    if isinstance(teacher_user_id, int):
                        # Прямое соответствие по user_id
                        try:
                            user_obj = db.get_user(int(teacher_user_id))
                        except Exception:
                            user_obj = None
                        if user_obj:
                            per_teacher.setdefault(teacher_user_id, []).append((task_id, _fmt(task_title or "Задача", task_id, general_errors)))
                        else:
                            teacher_name = _extract_teacher_full_name(task_fields, TEACHER_ID)
                            ambiguous_to_admin.append((teacher_name or "", task_id, general_errors))
                    else:
                        # Fallback: fuzzy-поиск по ФИО (только для форм которые это поддерживают)
                        teacher_name = _extract_teacher_full_name(task_fields, TEACHER_ID)
                        if use_fuzzy_search:
                            full_name, user_id = _fuzzy_find_user_by_full_name(teacher_name, threshold=0.85)
                            if full_name and user_id:
                                per_teacher.setdefault(user_id, []).append((task_id, _fmt(task_title or "Задача", task_id, general_errors)))
                            else:
                                ambiguous_to_admin.append((teacher_name or "", task_id, general_errors))
                        else:
                            # Для форм без fuzzy-поиска сразу в админы
                            ambiguous_to_admin.append((teacher_name or "", task_id, general_errors))

                # 2) Ошибки правила 3 → преподаватель из поля TEACHER_RULE3_ID (если есть)
                if rule3_errors and TEACHER_RULE3_ID:
                    teacher_user_id_r3 = _extract_teacher_user_id(task_fields, TEACHER_RULE3_ID)
                    if isinstance(teacher_user_id_r3, int):
                        try:
                            user_obj_r3 = db.get_user(int(teacher_user_id_r3))
                        except Exception:
                            user_obj_r3 = None
                        if user_obj_r3:
                            per_teacher.setdefault(teacher_user_id_r3, []).append((task_id, _fmt(task_title or "Задача", task_id, rule3_errors)))
                        else:
                            teacher_name_r3 = _extract_teacher_full_name(task_fields, TEACHER_RULE3_ID)
                            ambiguous_to_admin.append((teacher_name_r3 or "", task_id, rule3_errors))
                    else:
                        teacher_name_r3 = _extract_teacher_full_name(task_fields, TEACHER_RULE3_ID)
                        if use_fuzzy_search:
                            full_name_r3, user_id_r3 = _fuzzy_find_user_by_full_name(teacher_name_r3, threshold=0.85)
                            if full_name_r3 and user_id_r3:
                                per_teacher.setdefault(user_id_r3, []).append((task_id, _fmt(task_title or "Задача", task_id, rule3_errors)))
                            else:
                                ambiguous_to_admin.append((teacher_name_r3 or "", task_id, rule3_errors))
                        else:
                            ambiguous_to_admin.append((teacher_name_r3 or "", task_id, rule3_errors))

            # Подсчеты для отчета по форме
            sent_forms = sum(len(msgs) for msgs in per_teacher.values())
            sent_teachers = len(per_teacher)
            not_sent_forms = len(ambiguous_to_admin)
            unknown_teachers = len({(name or "").strip() for name, _, _ in ambiguous_to_admin if (name or "").strip()})
            
            total_sent_forms += sent_forms
            total_sent_teachers += sent_teachers
            total_not_sent += not_sent_forms
            total_unknown += unknown_teachers
            
            # Сохраняем отчет по форме
            form_reports.append(f"📋 {form_name}: разослано {sent_forms}, не разослано {not_sent_forms}")
            
            # Постановка в очередь для преподавателей
            import hashlib
            send_at = _tz_now(tz)
            
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
            
            # Логируем результат по форме
            db.log_event("form_check_summary", {
                "slot": slot,
                "form_id": form_id,
                "form_name": form_name,
                "teachers_found": sent_teachers,
                "ambiguous": not_sent_forms,
            })
            print(f"[form_checks] slot={slot} form='{form_name}' teachers_found={sent_teachers} ambiguous={not_sent_forms}")
            
        except Exception as e:
            db.log_event("form_check_error", {
                "slot": slot,
                "form_id": form_id,
                "error": str(e)
            })
            print(f"❌ Ошибка проверки формы {form_id}: {e}")
    
    # Создаем сводный админ-отчет
    if ADMIN_IDS:
        report_lines = [
            f"📊 Сводный отчёт за {target} (слот {slot})",
            f"Обработано форм: {len(form_ids)}",
            "",
        ] + form_reports + [
            "",
            f"🏆 ИТОГО:",
            f"Разослано: {total_sent_forms} задач, преподавателей: {total_sent_teachers}",
            f"Не разослано: {total_not_sent} задач",
            f"Преподавателей не найдено: {total_unknown}",
        ]
        report_text = "\n".join(report_lines)
        
        # Отправляем отчет админу
        short = {"today21": "t21", "yesterday12": "y12"}.get(slot, slot[:8])
        report_slot = f"report_{short}"
        
        import hashlib
        report_hash = hashlib.sha256((report_slot + target + str(total_sent_forms) + str(total_not_sent)).encode("utf-8")).hexdigest()
        
        send_at = _tz_now(tz)
        try:
            db.enqueue_preformatted(
                task_id=0,
                user_id=int(ADMIN_IDS[0]),
                send_at=send_at.astimezone(pytz.UTC).replace(tzinfo=None),
                slot=report_slot,
                message_text=report_text,
                dedupe_hash=report_hash,
            )
        except Exception as e:
            db.log_event("enqueue_admin_report_error", {"error": str(e), "slot": report_slot})


