# -*- coding: utf-8 -*-
"""XControlP — translations, window settings, icon styles, alerts and carried day tasks. Moved unchanged from XControlP.pyw."""
import datetime
import json
import os
import re
import threading
from .config import (ALERTS, ALERT_KEEP_DAYS, ALERT_STATES, CARRY_OPEN, DAY_COPY, HERE, LANGS, SETTINGS,
                     TRANSLATIONS)


def read_translations():
    """translations.json: {"en": {русский текст: перевод}, "he": {...}}. Нет файла или сломан — без переводов."""
    try:
        raw = json.loads(TRANSLATIONS.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in raw.items() if k in LANGS and isinstance(v, dict)}


# Настройки окна: язык, стиль значков, общий стиль. Чужие значения не принимаются.
# Стили значков — подпапки icons со своим style.json; «base» — прежние символы, картинок не нужно.
SETTING_DEFAULTS = {"lang": "ru", "icons": "comic", "theme": "dark", "scale": "100", "accent": "orange", "updates": "off",
                    "summary_card": "on"}
# Память окна (тоже в settings.json, ключ ui): свёрнутые карточки, сводка дня, скрытая крестиком на обзоре,
# и последний открытый ответ штаба в каждом разделе (зелёная метка гаснет, когда раздел открыт).
UI_KEY = re.compile(r"^[a-z0-9][a-z0-9:_|.-]{0,79}$")
UI_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
UI_SECTIONS = ("summary", "proposals", "digest", "digest-interesting", "digest-useful")   # the digest tabs: per kind
UI_FOLD_MAX = 300
SETTINGS_LOCK = threading.Lock()   # one read-modify-write of settings.json at a time


def setting_choices():
    return {"lang": LANGS, "icons": ("base",) + tuple(icon_styles()), "theme": ("dark", "light"),
            "scale": ("90", "100", "110", "125"), "accent": ("orange", "blue", "violet", "teal"),
            "updates": ("off", "on"), "summary_card": ("on", "off")}


def read_settings():
    try:
        raw = json.loads(SETTINGS.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    choices = setting_choices()
    result = {key: raw[key] if raw.get(key) in choices[key] else SETTING_DEFAULTS[key] for key in SETTING_DEFAULTS}
    if result["icons"] not in choices["icons"]:
        result["icons"] = "base"   # папки стиля нет — прежние символы
    result["ui"] = clean_ui(raw.get("ui"))
    return result


def clean_ui(raw):
    """Память окна из settings.json: только проверенные значения, остальное отбрасывается."""
    raw = raw if isinstance(raw, dict) else {}
    folded = raw.get("collapsed") if isinstance(raw.get("collapsed"), list) else []
    folded = list(dict.fromkeys(k for k in folded if isinstance(k, str) and UI_KEY.fullmatch(k)))[:UI_FOLD_MAX]
    hidden = raw.get("summary_hidden")
    hidden = hidden if isinstance(hidden, str) and UI_ID.fullmatch(hidden) else ""
    seen = raw.get("seen") if isinstance(raw.get("seen"), dict) else {}
    seen = {k: v for k, v in seen.items() if k in UI_SECTIONS and isinstance(v, str) and UI_ID.fullmatch(v)}
    return {"collapsed": folded, "summary_hidden": hidden, "seen": seen}


def write_settings(settings):
    """settings.json through a temporary file of its own (process and thread), then data.js."""
    temporary = SETTINGS.with_name(f"settings.json.{os.getpid()}.{threading.get_ident()}.tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, SETTINGS)


def rebuild():
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()


def save_ui(query):
    """Память окна: POST /ui?op=fold&key=…&on=1|0 (стрелка на карточке), op=hide-summary&id=… (крестик на сводке дня
    в обзоре), op=seen&section=summary|proposals|digest&id=… (раздел с ответом открыт — зелёная метка гаснет)."""
    q = lambda key: ((query or {}).get(key) or [""])[0]
    with SETTINGS_LOCK:
        result = change_ui(q, read_settings())
    if result["ok"]:
        rebuild()
    return result


def change_ui(q, settings):
    """One change of the window's memory, inside SETTINGS_LOCK; written only when valid."""
    op, ui = q("op"), settings["ui"]
    if op == "fold":
        key, on = q("key"), q("on")
        if not UI_KEY.fullmatch(key) or on not in ("0", "1"):
            return {"ok": False, "error": "нет ключа карточки"}
        folded = [k for k in ui["collapsed"] if k != key] + ([key] if on == "1" else [])
        ui["collapsed"] = folded[-UI_FOLD_MAX:]
    elif op == "hide-summary":
        if not UI_ID.fullmatch(q("id")):
            return {"ok": False, "error": "нет id сводки"}
        ui["summary_hidden"] = q("id")
    elif op == "seen":
        if q("section") not in UI_SECTIONS or not UI_ID.fullmatch(q("id")):
            return {"ok": False, "error": "нет раздела или id ответа"}
        ui["seen"][q("section")] = q("id")
    else:
        return {"ok": False, "error": f"неизвестное действие: {op!r}"}
    write_settings(settings)
    return {"ok": True, "op": op, "ui": ui}


def save_settings(query):
    """Кнопки языков и панель «Настройки»: POST /settings?lang=en (или icons=…, theme=…) → settings.json → data.js."""
    query = query or {}
    changes = {}
    for key, allowed in setting_choices().items():
        if key in query:
            value = (query.get(key) or [""])[0]
            if value not in allowed:
                return {"ok": False, "error": f"неизвестное значение {key}: {value!r}"}
            changes[key] = value
    if not changes:
        return {"ok": False, "error": "нечего сохранять"}
    with SETTINGS_LOCK:
        write_settings(dict(read_settings(), **changes))
    rebuild()
    return dict({"ok": True}, **changes)


def read_alerts():
    """alerts.json: {"marks": {ключ тревоги: {"state": "repair"|"dismissed", "at": "ГГГГ-ММ-ДД"}}}. Нет файла — отметок нет."""
    try:
        raw = json.loads(ALERTS.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    marks = raw.get("marks") if isinstance(raw, dict) else None
    if not isinstance(marks, dict):
        return {}
    return {k: {"state": v["state"], "at": str(v.get("at", ""))} for k, v in marks.items()
            if isinstance(k, str) and isinstance(v, dict) and v.get("state") in ALERT_STATES}


def save_alert(query):
    """Кнопки тревог в окне: POST /alerts?key=…&state=repair|dismissed|active → alerts.json → data.js.
    repair — «в починке», dismissed — «убрана», active — отметка снята (тревога снова обычная)."""
    key = ((query or {}).get("key") or [""])[0]
    state = ((query or {}).get("state") or [""])[0]
    if not key or len(key) > 300 or "\n" in key:
        return {"ok": False, "error": "нет ключа тревоги"}
    if state not in ALERT_STATES + ("active",):
        return {"ok": False, "error": f"неизвестная отметка: {state!r}"}
    today = datetime.date.today()
    oldest = (today - datetime.timedelta(days=ALERT_KEEP_DAYS)).isoformat()
    marks = {k: v for k, v in read_alerts().items() if v["at"] >= oldest}
    if state == "active":
        marks.pop(key, None)
    elif marks.get(key, {}).get("state") != state:
        marks[key] = {"state": state, "at": today.isoformat()}
    temporary = ALERTS.with_name(f"alerts.json.{os.getpid()}.tmp")
    temporary.write_text(json.dumps({"marks": marks}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, ALERTS)
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()
    return {"ok": True, "key": key, "state": state}


def read_carried():
    """Тревога «переносы на завтра»: открытые задачи плана дня с цепочкой переносов.
    Читается копия day.json (базу открывает только хранилище плана дня). Порог тревоги (3 переноса) — в окне.
    Цепочка считается по полю moved_from; если начало цепочки старше копии, счёт меньше настоящего."""
    try:
        raw = json.loads(DAY_COPY.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    days = raw.get("days") if isinstance(raw, dict) else None
    if not isinstance(days, dict):
        return []
    items = {}
    for day in days.values():
        if not isinstance(day, dict):
            continue
        for it in day.get("items") or []:
            if isinstance(it, dict) and isinstance(it.get("id"), str):
                items[it["id"]] = it
    found = []
    for it in items.values():
        if it.get("status") not in CARRY_OPEN or not it.get("moved_from"):
            continue
        carries, root, seen = 0, it, set()
        while root.get("moved_from") in items and root["id"] not in seen:
            seen.add(root["id"])
            root = items[root["moved_from"]]
            carries += 1
        found.append({"id": it["id"], "root": root["id"], "title": str(it.get("title") or ""), "project_id": str(it.get("project_id") or ""),
                      "carries": carries, "first_day": str(root.get("day") or ""), "day": str(it.get("day") or "")})
    return sorted(found, key=lambda x: (-x["carries"], x["day"], x["id"]))
# Значки меню: только png с простыми латинскими именами из папки icons, больше ничего.
ICONS_DIR = HERE / "icons"
ICON_PATH = re.compile(r"^/icons/([a-z0-9][a-z0-9-]{0,29})/([a-z0-9][a-z0-9-]{0,39})\.png$")
STYLE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,29}$")


def icon_styles():
    """Стили значков: подпапки icons с style.json {"id", "name": {ru, en, he}, "about": {…}}.
    Без картинок, с неверным id или с id «base» — пропускаются; два стиля с одним id — берётся тот, где картинок больше."""
    found = {}
    try:
        folders = sorted(p for p in ICONS_DIR.iterdir() if p.is_dir())
    except OSError:
        return found
    for folder in folders:
        try:
            raw = json.loads((folder / "style.json").read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        sid = raw.get("id") if isinstance(raw, dict) else None
        if not isinstance(sid, str) or not STYLE_ID.match(sid) or sid == "base":
            continue
        count = sum(1 for _ in folder.glob("*.png"))
        if count and (sid not in found or count > found[sid]["count"]):
            found[sid] = {"id": sid, "folder": folder, "count": count,
                          "name": raw["name"] if isinstance(raw.get("name"), dict) else {},
                          "about": raw["about"] if isinstance(raw.get("about"), dict) else {}}
    return found


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .build import (LAST_STAMPS, SYNC_LOCK, build, stamps)  # noqa: E402
