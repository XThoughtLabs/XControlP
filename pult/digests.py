# -*- coding: utf-8 -*-
"""XControlP — the glue to digest_store.py (news digests). Moved unchanged from XControlP.pyw."""
import importlib.util
import json
import os
from .config import (DIGEST_MODULE, SOURCE)


# ---------------------------------------------------------------- сводки

_DIGEST = []
DIGEST_PROBLEM = ["Нет файла digest_store.py рядом с Пультом."]


def digest_repo():
    """Репозиторий сводок: переменная окружения PULT_DIGEST_REPO или ключ digest_repo в projects.json.
    Не задан — None: раздел «Сводки» пуст, ни одна команда git не запускается. Репозитория по умолчанию нет."""
    value = os.environ.get("PULT_DIGEST_REPO") or ""
    if not value.strip():
        try:
            data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            data = {}
        value = str(data.get("digest_repo") or "") if isinstance(data, dict) else ""
    return os.path.expanduser(value.strip()) if value.strip() else None


def digest_topics():
    """Свои темы сводок: ключ digest_topics в projects.json (проверяет digest_store.extra_topics)."""
    try:
        data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    topics = data.get("digest_topics") if isinstance(data, dict) else None
    return topics if isinstance(topics, dict) else {}


def digest_store():
    """Сводки (digest_store.py рядом с Пультом): модуль загружается один раз, хранилище создаётся заново,
    когда сменился репозиторий сводок. Не загрузилось — None (причина в DIGEST_PROBLEM)."""
    if not _DIGEST:
        module = None
        if DIGEST_MODULE.is_file():
            try:
                spec = importlib.util.spec_from_file_location("pult_digest", DIGEST_MODULE)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as exc:
                DIGEST_PROBLEM[0] = f"digest_store.py не загрузился: {type(exc).__name__}: {exc}"
                module = None
        _DIGEST.append({"module": module, "repo": None, "topics": None, "store": None})
    entry = _DIGEST[0]
    if entry["module"] is None:
        return None
    repo, topics = digest_repo(), digest_topics()
    if entry["store"] is None or entry["repo"] != repo or entry["topics"] != topics:
        try:
            entry["store"] = entry["module"].Digests(repo, topics)
        except Exception as exc:
            DIGEST_PROBLEM[0] = f"digest_store.py не загрузился: {type(exc).__name__}: {exc}"
            entry["store"] = None
            return None
        entry["repo"], entry["topics"] = repo, topics
    return entry["store"]


def digest_view():
    """Сводки и отметки для окна (data.js). Ошибка — текстом в окно, Пульт работает дальше."""
    store = digest_store()
    if store is None:
        return {"ok": False, "error": DIGEST_PROBLEM[0], "digests": []}
    try:
        return store.view()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "digests": []}


def digest_stamp():
    store = digest_store()
    try:
        return store.stamp() if store is not None else None
    except Exception:
        return None


def digest_sync():
    """Кнопка «Синхронизировать данные»: новые сводки с GitHub и отправка отметок."""
    store = digest_store()
    if store is None:
        return {"ok": False, "error": DIGEST_PROBLEM[0]}
    if store.repo is None:
        return None          # репозиторий сводок не задан: синхронизировать нечего, git не запускается
    try:
        return store.sync()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def digest_mark(query):
    """Кнопки «Интересно» и «Полезно»: POST /digest/mark?date=…&id=…&kind=interesting|useful&value=1|0."""
    q = lambda key: ((query or {}).get(key) or [""])[0]
    store = digest_store()
    if store is None:
        return {"ok": False, "error": DIGEST_PROBLEM[0]}
    try:
        result = store.mark(q("date"), q("id"), q("kind"), q("value") == "1")
    except Exception as exc:
        return {"ok": False, "error": str(exc) if exc.__class__.__name__ == "DigestError" else f"{type(exc).__name__}: {exc}"}
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()
    return result


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .build import (LAST_STAMPS, SYNC_LOCK, build, stamps)  # noqa: E402
