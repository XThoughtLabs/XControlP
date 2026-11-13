# -*- coding: utf-8 -*-
"""XControlP — ideas: the ideas files, the ideas base, the history of statuses. Moved unchanged from XControlP.pyw."""
import datetime
import json
import os
import pathlib
import re
import sqlite3
import sys
import time
from .config import (HERE, HISTORY)

# Номер идеи: буква и число — A-17, B-4…
ROW = re.compile(r"^\|\s*([A-Z]-\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$")
HEAD = re.compile(r"^##\s+([A-Z]-\d+)\.\s*(.+?)\s*$")
LABEL = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
DATE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")


def clean(text):
    """Убирает разметку Markdown, которая не нужна на экране: **жирный** и `код`."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text.replace("`", "").strip()


def iso(date):
    m = DATE.match(date.strip())
    return f"{m[3]}-{m[2]}-{m[1]}" if m else date.strip()


def read_ideas(path):
    """Реестр идей (IDEAS.md) → список идей. Файл только читается."""
    try:
        text = path.read_text(encoding="utf-8-sig")
        changed = datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError as exc:
        return {"source": str(path), "error": f"Файл с идеями не читается: {path} ({exc.strerror or exc})"}

    summary, order, sections, current = {}, [], {}, None
    for line in text.splitlines():
        row = ROW.match(line)
        if row:
            key, date, title, status = (part.strip() for part in row.groups())
            if key not in summary:
                order.append(key)
            summary[key] = {"date": iso(date), "title": clean(title), "status": clean(status)}
            continue
        head = HEAD.match(line)
        if head:
            current = sections[head[1]] = {"title": clean(head[2]), "notes": []}
            continue
        if line.startswith("#"):
            current = None
            continue
        if current is None or not line.strip() or line.strip() == "---":
            continue
        notes = current["notes"]
        if re.match(r"^\s{2,}[-*]\s", line) and notes:
            notes[-1]["sub"].append(clean(line.strip()[2:]))
        elif re.match(r"^[-*]\s", line):
            item = line[2:].strip()
            label = LABEL.match(item)
            notes.append({"label": clean(label[1]) if label else "", "text": clean(label[2] if label else item), "sub": []})
        elif notes:
            notes[-1]["text"] += " " + clean(line)

    items = []
    for key in order + [k for k in sections if k not in summary]:
        top, section = summary.get(key, {}), sections.get(key, {})
        status = top.get("status") or next((n["text"] for n in section.get("notes", []) if n["label"].lower().startswith("статус")), "")
        items.append({
            "id": key,
            "date": top.get("date", ""),
            "title": top.get("title") or section.get("title", key),
            "full_title": section.get("title", ""),
            "status": status.rstrip("."),
            "notes": section.get("notes", []),
        })
    return {"source": str(path), "updated": changed, "items": items}


def idea_path(value):
    """Путь к файлу идей: относительный считается от папки программы."""
    path = pathlib.Path(os.path.expanduser(str(value)))
    return path if path.is_absolute() else HERE / path


def idea_sources(data):
    """Файлы идей → подотделы раздела «Идеи». ideas_files: [{id, title, about, path}, …];
    если списка нет — старое поле ideas_file (один файл идей). --ideas=ПУТЬ заменяет первый файл."""
    listed = data.get("ideas_files")
    sources = []
    if isinstance(listed, list) and listed:
        for i, item in enumerate(listed):
            if isinstance(item, dict):
                sources.append({"id": str(item.get("id") or f"set{i + 1}"), "title": str(item.get("title") or "Идеи"),
                                "about": str(item.get("about") or ""), "path": str(item.get("path") or "")})
    elif data.get("ideas_file"):
        sources.append({"id": "hq", "title": "Идеи", "about": "", "path": str(data["ideas_file"])})
    for arg in sys.argv[1:]:
        if arg.startswith("--ideas="):
            if not sources:
                sources.append({"id": "hq", "title": "Идеи", "about": "", "path": ""})
            sources[0]["path"] = arg[len("--ideas="):]
    seen = set()
    for item in sources:
        while item["id"] in seen:
            item["id"] += "_"
        seen.add(item["id"])
    return sources


def idea_kind(status):
    """Итог идеи по её статусу — те же правила, что в окне Пульта (ideaKind)."""
    s = (status or "").strip().lower()
    if s.startswith("сделано"):
        return "done"
    if s.startswith("в дорожной карте"):
        return "road"
    if s.startswith("решение"):
        return "decision"        # решение, ещё не выполнено — не идея
    if "исследовать" in s:
        return "explore"
    if s.startswith("отказ"):
        return "dropped"
    if s.startswith(("ждёт", "ждет", "отлож")):
        return "wait"
    if s.startswith("идея") and "на будущее" in s:
        return "future"          # отложена сознательно — не то же, что «не проверялась»
    return "idea"


def update_history(sets):
    """История итогов идей (ideas-history.json — файл самого Пульта; файлы идей не меняются).
    Новая запись — только когда итог идеи изменился. Для окна — дата начала истории и переходы."""
    today = datetime.date.today().isoformat()
    try:
        history = json.loads(HISTORY.read_text(encoding="utf-8-sig"))
        if not isinstance(history, dict) or not isinstance(history.get("ideas"), dict):
            raise ValueError("нет раздела ideas")
    except FileNotFoundError:
        history = {"version": 1, "started": today, "ideas": {}}
    except (OSError, ValueError) as exc:
        # Испорченный файл не переписываем: его можно восстановить вручную.
        return {"started": "", "transitions": [], "error": f"История идей не читается: {HISTORY} ({exc})"}
    changed = False
    for found in sets:
        for item in found.get("items", []):
            kind = idea_kind(item.get("status"))
            item["kind"] = kind
            track = history["ideas"].setdefault(found["id"] + ":" + item["id"], [])
            if not track or track[-1].get("kind") != kind:
                track.append({"date": today, "kind": kind, "status": item.get("status", "")})
                changed = True
    if changed:
        temporary = HISTORY.with_name(f"ideas-history.json.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(history, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(temporary, HISTORY)
    transitions = []
    for key, track in history["ideas"].items():
        set_id, _, idea_id = key.partition(":")
        for before, after in zip(track, track[1:]):
            transitions.append({"date": after.get("date", ""), "set": set_id, "id": idea_id,
                                "from": before.get("kind", ""), "to": after.get("kind", "")})
    transitions.sort(key=lambda t: (t["date"], t["set"], t["id"]), reverse=True)
    return {"started": history.get("started", today), "transitions": transitions[:300]}


def read_idea_sets(data):
    """Все подотделы идей. Ошибка одного файла не мешает другим: она показывается в его подотделе."""
    sets = []
    for item in idea_sources(data):
        if item["path"]:
            found = read_ideas(idea_path(item["path"]))
        else:
            found = {"source": "", "error": "Для подотдела «" + item["title"] + "» не указан путь к файлу (path в ideas_files)."}
        found.update(id=item["id"], title=item["title"], about=item["about"])
        sets.append(found)
    return sets


def ideas_db_path(data):
    value = data.get("ideas_db")
    return pathlib.Path(os.path.expanduser(str(value))) if value else None


def outcome(kind, status):
    """Итог для окна: в базе «на будущее» и «решение» хранятся как «идея», отличаются словами статуса."""
    return idea_kind(status) if kind == "idea" else kind


def read_ideas_db(data):
    """Общая база идей → {"sets", "history"}, {"error"} или None (база не указана). Только чтение:
    база открывается в режиме ro, всё читается одним снимком."""
    path = ideas_db_path(data)
    if not path:
        return None
    for attempt in range(4):        # исполнитель может писать в эту секунду — тогда чуть подождать
        try:
            if not path.is_file():
                raise OSError("файла нет")
            con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10, isolation_level=None)
            con.row_factory = sqlite3.Row
            try:
                con.execute("BEGIN")
                depts = con.execute("SELECT code, name, owner FROM depts ORDER BY pos, code").fetchall()
                ideas = con.execute("SELECT * FROM ideas ORDER BY dept, num").fetchall()
                notes = con.execute("SELECT idea, label, text, sub FROM notes ORDER BY idea, pos").fetchall()
                links = con.execute("SELECT a, b, note FROM links ORDER BY a, b").fetchall()
                log = con.execute("SELECT idea, at, kind, status FROM status_log ORDER BY rid").fetchall()
                created = con.execute("SELECT value FROM meta WHERE key = 'created_at'").fetchone()
                con.execute("COMMIT")
            finally:
                con.close()
            break
        except sqlite3.Error as exc:
            if attempt == 3:
                return {"error": f"Общая база идей не читается: {path} ({exc}). Показаны файлы идей."}
            time.sleep(0.4)
        except OSError as exc:
            return {"error": f"Общая база идей не читается: {path} ({exc.strerror or exc}). Показаны файлы идей."}

    by_note, by_link = {}, {}
    for n in notes:
        try:
            sub = json.loads(n["sub"] or "[]")
        except ValueError:
            sub = []
        sub = [clean(re.sub(r"^[-*]\s+", "", str(line).strip())) for line in sub if str(line).strip()]
        by_note.setdefault(n["idea"], []).append({"label": clean(n["label"] or ""), "text": clean(n["text"] or ""), "sub": sub})
    for link in links:               # связь могли записать оба отдела — без повторов
        by_link.setdefault(link["a"], set()).add(link["b"])
        by_link.setdefault(link["b"], set()).add(link["a"])
    about = {item["id"]: item["about"] for item in idea_sources(data)}
    sets, dept_of = [], {}
    for dept in depts:
        rows = [r for r in ideas if r["dept"] == dept["code"]]
        if not rows:
            continue
        items = []
        for r in rows:
            dept_of[r["id"]] = dept["code"]
            items.append({"id": r["id"], "date": r["date"], "title": clean(r["title"]), "full_title": clean(r["full_title"] or ""),
                          "status": clean(r["status"]).rstrip("."), "kind": outcome(r["kind"], r["status"]), "project": r["project"] or "",
                          "links": sorted(by_link.get(r["id"], [])), "notes": by_note.get(r["id"], [])})
        updated = max(r["updated_at"] for r in rows)[:16].replace("T", " ")
        sets.append({"id": dept["code"], "title": dept["name"], "source": str(path), "updated": updated, "from_db": True,
                     "about": about.get(dept["code"]) or ("Ведёт: " + dept["owner"] if dept["owner"] else ""), "items": items})
    last, transitions, born_done = {}, [], []
    for r in log:
        kind = outcome(r["kind"], r["status"])
        before = last.get(r["idea"])
        if before is not None and before != kind and r["idea"] in dept_of:
            transitions.append({"date": r["at"][:10], "set": dept_of[r["idea"]], "id": r["idea"], "from": before, "to": kind})
        elif before is None and kind == "done" and r["idea"] in dept_of:
            # идея записана сразу сделанной — перехода нет, но для «Статистики» это идея, сделанная в этот день
            born_done.append({"date": r["at"][:10], "set": dept_of[r["idea"]], "id": r["idea"]})
        last[r["idea"]] = kind
    transitions.sort(key=lambda t: (t["date"], t["set"], t["id"]), reverse=True)
    born_done.sort(key=lambda t: (t["date"], t["set"], t["id"]), reverse=True)
    history = {"started": (created[0] if created else "")[:10], "transitions": transitions[:300], "born_done": born_done[:300], "from_db": True}
    return {"sets": sets, "history": history}
