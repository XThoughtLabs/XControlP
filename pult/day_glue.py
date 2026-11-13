# -*- coding: utf-8 -*-
"""XControlP — the glue to day_store.py (the day plan). Moved unchanged from XControlP.pyw."""
import datetime
import importlib.util
import json
import time
from .config import (DAY_EVERY, DAY_MODULE, HERE)


# ---------------------------------------------------------------- план дня

_DAY = []
DAY_PROBLEM = ["Нет файла day_store.py рядом с Пультом."]


def day_store():
    """Хранилище плана дня (day_store.py рядом с Пультом); загружается один раз. Не загрузилось — None (причина в DAY_PROBLEM)."""
    if not _DAY:
        store = None
        if DAY_MODULE.is_file():
            try:
                spec = importlib.util.spec_from_file_location("pult_day", DAY_MODULE)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                store = module.Store(HERE)
            except Exception as exc:
                DAY_PROBLEM[0] = f"day_store.py не загрузился: {type(exc).__name__}: {exc}"
                store = None
        _DAY.append(store)
    return _DAY[0]


def day_error(exc):
    return {"ok": False, "error": str(exc) if exc.__class__.__name__ == "DayError" else f"{type(exc).__name__}: {exc}"}


def day_view(query):
    """GET /day.json?day=2026-10-07 — задачи дня; сначала применить ждущие запросы Claude."""
    store = day_store()
    if store is None:
        return {"ok": False, "error": DAY_PROBLEM[0]}, 200
    day = ((query or {}).get("day") or [datetime.date.today().isoformat()])[0]
    try:
        applied = store.process_inbox()
        result = store.view(day)
        result["applied"] = applied
        return result, 200
    except Exception as exc:
        return day_error(exc), 200


def day_review(query):
    """GET /day-review.json?from=…&to=… — итоги дней для вкладки «Итоги дней»."""
    store = day_store()
    if store is None:
        return {"ok": False, "error": DAY_PROBLEM[0]}, 200
    today = datetime.date.today()
    first = ((query or {}).get("from") or [(today - datetime.timedelta(days=370)).isoformat()])[0]
    last = ((query or {}).get("to") or [(today + datetime.timedelta(days=31)).isoformat()])[0]
    try:
        store.process_inbox()
        return store.review(first, last), 200
    except Exception as exc:
        return day_error(exc), 200


def day_op(body):
    """POST /day/op {"day": …, "ops": [...]} — изменения из окна; ответ — свежий вид дня."""
    store = day_store()
    if store is None:
        return {"ok": False, "error": DAY_PROBLEM[0]}, 200
    try:
        request = json.loads(body.decode("utf-8"))
        if not isinstance(request, dict):
            raise ValueError("нужен объект")
        results = store.apply(request.get("ops"), by="pult")
        result = store.view(request.get("day") or datetime.date.today().isoformat())
        result["results"] = results
        return result, 200
    except Exception as exc:
        return day_error(exc), 200


def day_keeper():
    """Пока Пульт открыт: запросы Claude из day-inbox применяются сами, каждые 10 секунд."""
    store = day_store()
    if store is None:
        return
    while True:
        try:
            if store.pending():
                store.process_inbox()
        except Exception:
            pass
        time.sleep(DAY_EVERY)
