# -*- coding: utf-8 -*-
"""XControlP — the glue to calendar_google.py. Moved unchanged from XControlP.pyw."""
import importlib.util
import re
import time
from .config import (CALENDAR_EVERY, CALENDAR_MODULE)


_GCAL = []


def gcal():
    """Модуль календаря (calendar_google.py рядом с Пультом); загружается один раз. Нет файла — None."""
    if not _GCAL:
        module = None
        if CALENDAR_MODULE.is_file():
            try:
                spec = importlib.util.spec_from_file_location("pult_gcal", CALENDAR_MODULE)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception:
                module = None
        _GCAL.append(module)
    return _GCAL[0]


def calendar_data():
    """Для окна: скачанные события (calendar.json) и что настроено — без секретов."""
    module = gcal()
    if module is None:
        return {"available": False}
    cache = module.read_json(module.CACHE) or {}
    return dict(cache, available=True, setup=module.setup())


def calendar_connected(module):
    """Есть ли хоть одно разрешение Google (старый модуль знает только google-token.json)."""
    return module.connected() if hasattr(module, "connected") else module.TOKEN.is_file()


def calendar_sync_quiet():
    """Обновить календарь, если Пульт уже подключён к Google. Ошибка календаря не мешает остальному."""
    module = gcal()
    if module is None or not calendar_connected(module):
        return None
    try:
        return module.sync()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def calendar_login(query=None, add=False):
    """Кнопки «Войти в Google» / «Войти снова» / «+ Аккаунт»: окно Google открывается в браузере, вход идёт в фоне."""
    module = gcal()
    if module is None:
        return {"ok": False, "error": "Нет файла calendar_google.py рядом с Пультом."}
    if not module.CLIENT.is_file():
        return {"ok": False, "error": "Нет файла google-client.json в папке Пульта."}
    hint = ((query or {}).get("account") or [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", hint or "x@x"):
        hint = ""
    try:
        started = module.start_login(add=add, hint=hint)
    except TypeError:                     # старый calendar_google.py без нескольких аккаунтов
        started = module.start_login()
    return {"ok": True, "started": started}


def calendar_add(query=None):
    return calendar_login(query, add=True)


def calendar_sync_now():
    """Кнопка «Обновить» в разделе «Календарь»."""
    module = gcal()
    if module is None:
        return {"ok": False, "error": "Нет файла calendar_google.py рядом с Пультом."}
    with SYNC_LOCK:
        result = module.sync()
        build()
        LAST_STAMPS[0] = stamps()
    return result


def calendar_keeper():
    """Пока Пульт открыт: календарь обновляется при запуске (если устарел) и каждые 30 минут."""
    module = gcal()
    if module is None:
        return
    first = True
    while True:
        if calendar_connected(module):
            age = module.cache_age_minutes()
            if not first or age is None or age > 30:
                with SYNC_LOCK:
                    try:
                        module.sync()
                    except Exception:
                        pass
        first = False
        time.sleep(CALENDAR_EVERY)


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .build import (LAST_STAMPS, SYNC_LOCK, build, stamps)  # noqa: E402
