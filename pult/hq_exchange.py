# -*- coding: utf-8 -*-
"""XControlP — requests to HQ, answers and proposals. Moved unchanged from XControlP.pyw."""
import datetime
import json
import os
import re
from .config import (ANSWERS_DIR, ANSWER_MAX, PROPOSALS, PROPOSAL_KEY, PROPOSAL_STATES, REQUESTS_DIR,
                     REQUEST_KINDS)


# ---------------------------------------------------------------- запросы штабу и предложения

def write_request(query, body):
    """POST /request?kind=summary|proposals, тело — снимок Пульта из окна (JSON-объект) → «requests/request-…-kind.json».
    Запрос лежит в файле; пользователь просит штаб в чате разобрать его; ответ штаба — в папке answers."""
    kind = ((query or {}).get("kind") or [""])[0]
    if kind not in REQUEST_KINDS:
        return {"ok": False, "error": f"неизвестный вид запроса: {kind!r}"}
    try:
        snapshot = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {"ok": False, "error": "снимок Пульта не читается"}
    if not isinstance(snapshot, dict):
        return {"ok": False, "error": "снимок Пульта: нужен объект"}
    now = datetime.datetime.now()
    REQUESTS_DIR.mkdir(exist_ok=True)
    rid = "request-" + now.strftime("%Y-%m-%d-%H%M%S") + "-" + kind
    n = 1
    while (REQUESTS_DIR / (rid + ".json")).exists():
        n += 1
        rid = "request-" + now.strftime("%Y-%m-%d-%H%M%S") + "-" + kind + "-" + str(n)
    record = {"format": "pult-request", "version": 1, "id": rid, "kind": kind, "created": now.strftime("%Y-%m-%dT%H:%M:%S"),
              "lang": read_settings().get("lang", "ru"), "snapshot": snapshot}
    temporary = REQUESTS_DIR / (rid + f".json.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, REQUESTS_DIR / (rid + ".json"))
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()
    return {"ok": True, "id": rid}


def lang_text(value):
    """Текст ответа штаба: {"ru", "en", "he"}, все три — непустые строки."""
    return isinstance(value, dict) and all(isinstance(value.get(k), str) and value[k].strip() for k in ("ru", "en", "he"))


def check_answer(data):
    """Ответ штаба (format pult-answer, version 1). Пустая строка — всё верно, иначе — что не так."""
    if not isinstance(data, dict) or data.get("format") != "pult-answer" or data.get("version") != 1:
        return "не pult-answer версии 1"
    if data.get("kind") not in REQUEST_KINDS:
        return "вид ответа — summary или proposals"
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", str(data.get("written") or "")):
        return "нет времени written (ГГГГ-ММ-ДДTЧЧ:ММ)"
    if not lang_text(data.get("title")):
        return "заголовок title — на трёх языках"
    if "summary" in data and not lang_text(data["summary"]):
        return "сводка summary — на трёх языках"
    if not isinstance(data.get("blocks", []), list):
        return "blocks — список"
    seen = set()
    for item in data.get("proposals", []) if isinstance(data.get("proposals", []), list) else [None]:
        if not isinstance(item, dict) or not re.match(r"^[a-z0-9][a-z0-9-]{0,39}$", str(item.get("id") or "")) or item["id"] in seen:
            return "предложение: нужен свой id (латиница, цифры, дефис)"
        seen.add(item["id"])
        if not lang_text(item.get("text")) or ("why" in item and not lang_text(item["why"])):
            return f"предложение {item['id']}: текст на трёх языках"
        if item.get("project") is not None and not isinstance(item.get("project"), str):
            return f"предложение {item['id']}: project — строка"
    return ""


def read_answers():
    """Ответы штаба из «answers/*.json», новые сверху. Плохой файл не теряется: показывается с причиной."""
    found = []
    if not ANSWERS_DIR.is_dir():
        return found
    for path in ANSWERS_DIR.glob("*.json"):
        entry = {"file": path.name, "id": path.stem, "data": None, "error": ""}
        try:
            if path.stat().st_size > ANSWER_MAX:
                raise ValueError("файл больше 2 МБ")
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            problem = check_answer(data)
            if problem:
                raise ValueError(problem)
            entry["data"] = data
        except (OSError, ValueError) as exc:
            entry["error"] = str(exc)
        found.append(entry)
    found.sort(key=lambda e: (str((e["data"] or {}).get("written") or ""), e["file"]), reverse=True)
    return found


def read_requests(answers):
    """Запросы из «requests/*.json»: id, вид, время и есть ли на него ответ (поле request в ответе)."""
    done = {str((a["data"] or {}).get("request") or "") for a in answers}
    found = []
    if not REQUESTS_DIR.is_dir():
        return found
    for path in REQUESTS_DIR.glob("request-*.json"):
        kind = "summary" if "-summary" in path.stem else "proposals" if "-proposals" in path.stem else ""
        m = re.match(r"^request-(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})(\d{2})", path.stem)
        created = f"{m[1]}T{m[2]}:{m[3]}:{m[4]}" if m else ""
        found.append({"id": path.stem, "kind": kind, "created": created, "answered": path.stem in done})
    found.sort(key=lambda r: r["id"], reverse=True)
    return found


def read_proposal_marks():
    """proposals.json: {"marks": {"ответ|предложение": {"state": "accepted"|"declined", "at": "ГГГГ-ММ-ДД"}}}."""
    try:
        raw = json.loads(PROPOSALS.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    marks = raw.get("marks") if isinstance(raw, dict) else None
    if not isinstance(marks, dict):
        return {}
    return {k: {"state": v["state"], "at": str(v.get("at", ""))} for k, v in marks.items()
            if isinstance(k, str) and isinstance(v, dict) and v.get("state") in PROPOSAL_STATES}


def save_proposal(query):
    """POST /proposal?key=ответ|предложение&state=accepted|declined|active → proposals.json → data.js."""
    key = ((query or {}).get("key") or [""])[0]
    state = ((query or {}).get("state") or [""])[0]
    if not PROPOSAL_KEY.match(key):
        return {"ok": False, "error": "нет ключа предложения"}
    if state not in PROPOSAL_STATES + ("active",):
        return {"ok": False, "error": f"неизвестная отметка: {state!r}"}
    marks = read_proposal_marks()
    if state == "active":
        marks.pop(key, None)
    elif marks.get(key, {}).get("state") != state:
        marks[key] = {"state": state, "at": datetime.date.today().isoformat()}
    temporary = PROPOSALS.with_name(f"proposals.json.{os.getpid()}.tmp")
    temporary.write_text(json.dumps({"marks": marks}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, PROPOSALS)
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()
    return {"ok": True, "key": key, "state": state}


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .settings import (read_settings)  # noqa: E402
from .build import (LAST_STAMPS, SYNC_LOCK, build, stamps)  # noqa: E402
