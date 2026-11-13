# -*- coding: utf-8 -*-
"""XControlP — our services and idea flags. Moved unchanged from XControlP.pyw."""
import datetime
import json
import os
from .config import (FLAGS, IDEA_ID, SOURCE)


def read_services():
    """flags.json — реестр услуг: {"services": {номер идеи: {"added": "ГГГГ-ММ-ДД", "flag": true|false, "flag_at": "ГГГГ-ММ-ДД"}}}.
    Услуга закреплена за отделом услуг: снятый флажок её не убирает. Старый вид {"flags": {номер: {"at": …}}} читается
    как услуги с флажком и переписывается в новый при первой записи. Нет файла — услуг нет."""
    try:
        raw = json.loads(FLAGS.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    old = raw.get("flags")
    if isinstance(old, dict):
        for k, v in old.items():
            if isinstance(k, str) and IDEA_ID.match(k) and isinstance(v, dict):
                at = str(v.get("at", ""))
                out[k] = {"added": at, "flag": True, "flag_at": at}
    new = raw.get("services")
    if isinstance(new, dict):
        for k, v in new.items():
            if isinstance(k, str) and IDEA_ID.match(k) and isinstance(v, dict):
                out[k] = {"added": str(v.get("added", "")), "flag": bool(v.get("flag")), "flag_at": str(v.get("flag_at", ""))}
    return out


def write_services(services):
    temporary = FLAGS.with_name(f"flags.json.{os.getpid()}.tmp")
    temporary.write_text(json.dumps({"services": dict(sorted(services.items()))}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, FLAGS)
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()


def known_idea_ids():
    """Номера всех идей, которые видит Пульт: из базы идей, а если её нет — из файлов идей."""
    data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    found = read_ideas_db(data)
    sets = found["sets"] if found and found.get("sets") else read_idea_sets(data)
    return {str(it.get("id")) for s in (sets or []) for it in (s.get("items") or [])}


def query_id(query):
    return ((query or {}).get("id") or [""])[0]


def save_flag(query):
    """Кнопка в карточке идеи: POST /idea/flag?id=A-37&on=1|0 → flags.json → data.js. База идей не меняется.
    on=1: идея становится услугой (если ещё не услуга) и получает зелёный флажок; on=0: флажок снят, услуга остаётся."""
    idea = query_id(query)
    on = ((query or {}).get("on") or [""])[0]
    if not IDEA_ID.match(idea):
        return {"ok": False, "error": f"неверный номер идеи: {idea!r}"}
    if on not in ("1", "0"):
        return {"ok": False, "error": f"неизвестное значение: {on!r}"}
    services = read_services()
    today = datetime.date.today().isoformat()
    if on == "1":
        if idea not in services:
            try:
                known = known_idea_ids()
            except (OSError, ValueError) as exc:
                return {"ok": False, "error": f"идеи не читаются: {exc}"}
            if idea not in known:
                return {"ok": False, "error": f"нет такой идеи: {idea}"}
            services[idea] = {"added": today, "flag": True, "flag_at": today}
        elif not services[idea]["flag"]:
            services[idea].update(flag=True, flag_at=today)
    elif idea in services and services[idea]["flag"]:
        services[idea].update(flag=False, flag_at=today)
    write_services(services)
    return {"ok": True, "id": idea, "on": on == "1", "service": idea in services}


def remove_service(query):
    """Кнопка «Убрать из услуг» (после подтверждения в окне): POST /idea/service-remove?id=… — услуга уходит
    из отдела услуг; сама идея в базе остаётся."""
    idea = query_id(query)
    if not IDEA_ID.match(idea):
        return {"ok": False, "error": f"неверный номер идеи: {idea!r}"}
    services = read_services()
    if idea not in services:
        return {"ok": True, "id": idea, "removed": False}
    services.pop(idea)
    write_services(services)
    return {"ok": True, "id": idea, "removed": True}


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .ideas import (read_idea_sets, read_ideas_db)  # noqa: E402
from .build import (LAST_STAMPS, SYNC_LOCK, build, stamps)  # noqa: E402
