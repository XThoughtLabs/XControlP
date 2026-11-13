# -*- coding: utf-8 -*-
"""XControlP — auto.json, the build of data.js and the watch for changes. Moved unchanged from XControlP.pyw."""
import json
import os
import threading
from .config import (ALERTS, ANSWERS_DIR, AUTO, CALENDAR_FILES, DAY_COPY, FLAGS, PROPOSALS, REQUESTS_DIR,
                     RESEARCH, RESEARCH_DIR, SETTINGS, SOURCE, TARGET, TRANSLATIONS)


def read_auto():
    try:
        return json.loads(AUTO.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def merge_auto(data, auto):
    """Итог синхронизации (auto.json) → в данные окна. Этап не уходит назад, ручные записи не теряются."""
    if not auto:
        return 0
    seen = {(h.get("date"), h.get("project"), h.get("text")) for h in data.get("history", [])}
    added = 0
    for project in data.get("projects", []):
        result = (auto.get("projects") or {}).get(project.get("id"))
        if not result or not result.get("ok"):
            continue
        current = result.get("current")
        if isinstance(current, int) and current >= project.get("current", 0):
            project["current"] = current
        move = result.get("last_move")
        if move and move > (project.get("last_move") or ""):
            project["last_move"] = move
        project["auto"] = {"kind": result.get("kind"), "activity": result.get("activity"), "synced": auto.get("synced")}
        for event in result.get("events", []):
            key = (event.get("date"), project.get("id"), event.get("text"))
            if key not in seen:
                seen.add(key)
                data.setdefault("history", []).append({"date": key[0], "project": key[1], "text": key[2], "auto": True})
                added += 1
    data["sync"] = {"synced": auto.get("synced"), "notes": auto.get("notes", []), "errors": auto.get("errors", [])}
    if isinstance(auto.get("stats"), dict):          # раздел «Статистика»: уроки и коммиты по дням (сборщик)
        data["stats"] = dict(auto["stats"], synced=auto.get("synced"))
    return added


def build():
    """projects.json (+ идеи, + auto.json) → data.js. Ошибка в projects.json попадает в окно текстом, а не теряется."""
    try:
        data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
        found = read_ideas_db(data)
        if found and found.get("sets"):
            sets, history = found["sets"], found["history"]
            data["idea_source"] = {"kind": "db", "path": str(ideas_db_path(data))}
        else:
            # Базы нет, она пуста или не читается — идеи из файлов, как раньше.
            sets = read_idea_sets(data)
            history = update_history(sets) if sets else None
            data["idea_source"] = {"kind": "files", "error": (found or {}).get("error", "")}
        if sets:
            data["idea_sets"] = sets
            data["ideas"] = sets[0]  # для старого окна, которое знает только один файл идей
            data["idea_history"] = history
        merge_auto(data, read_auto())
        data["calendar"] = calendar_data()
        data["translations"] = read_translations()
        data["settings"] = read_settings()
        data["icon_styles"] = [{k: v for k, v in st.items() if k != "folder"} for st in icon_styles().values()]
        data["alerts"] = read_alerts()
        data["day_carried"] = read_carried()
        data["answers"] = read_answers()
        data["requests"] = read_requests(data["answers"])
        data["proposal_marks"] = read_proposal_marks()
        data["services"] = read_services()
        data["research"] = read_research()
        data["reports"] = read_reports(data)
        data["digests"] = digest_view()
        text = "window.BOARD = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n"
    except (OSError, ValueError) as exc:
        data = None
        text = "window.BOARD = null;\nwindow.BOARD_ERROR = " + json.dumps(f"projects.json не читается: {exc}", ensure_ascii=False) + ";\n"
    temporary = TARGET.with_name(f"data.js.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, TARGET)
    return data


# ---------------------------------------------------------------- синхронизация

SYNC_LOCK = threading.Lock()


def watched_files():
    """Файлы, от которых зависит data.js: projects.json, auto.json, база идей (с журналом) и файлы идей."""
    files = [SOURCE, AUTO, TRANSLATIONS, SETTINGS, ALERTS, FLAGS, RESEARCH, DAY_COPY, PROPOSALS] + CALENDAR_FILES + sorted(RESEARCH_DIR.glob("*.md"))
    files += sorted(REQUESTS_DIR.glob("*.json")) + sorted(ANSWERS_DIR.glob("*.json"))
    files += sorted(ICONS_DIR.glob("*/style.json"))
    try:
        data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return files
    db = ideas_db_path(data)
    if db:
        files += [db, db.with_name(db.name + "-journal")]
    files += [idea_path(item["path"]) for item in idea_sources(data) if item["path"]]
    folder = reports_dir(data)
    files += sorted(folder.glob("*.md")) + sorted(folder.glob("*.json")) if folder.is_dir() else []
    mfolder = monthly_dir(data)
    files += sorted(mfolder.glob("*.md")) + sorted(mfolder.glob("*.json")) if mfolder.is_dir() else []
    root = git_root(folder) if folder.is_dir() else None
    if root:
        files += [root / ".git" / "refs" / "remotes" / "origin" / "main", root / ".git" / "packed-refs"]
    return files


def stamps():
    result = []
    for path in watched_files():
        try:
            st = path.stat()
            result.append((str(path), st.st_mtime_ns, st.st_size))
        except OSError:
            result.append((str(path), None, None))
    result.append(("digests", digest_stamp(), None))
    return result


LAST_STAMPS = [None]


def rebuild_if_changed():
    """Окно просит data.js — если источники изменились с прошлой сборки, сначала пересобрать.
    Во время синхронизации не мешаем: она сама соберёт data.js."""
    if not SYNC_LOCK.acquire(blocking=False):
        return
    try:
        now = stamps()
        if now != LAST_STAMPS[0]:
            build()
            LAST_STAMPS[0] = stamps()
    except Exception:
        pass
    finally:
        SYNC_LOCK.release()


def effective_stages():
    """Какие этапы показывает окно сейчас: projects.json с учётом прошлой синхронизации."""
    data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    merge_auto(data, read_auto())
    return {p.get("id"): p.get("current", 0) for p in data.get("projects", [])}


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .ideas import (idea_path, idea_sources, ideas_db_path, read_idea_sets, read_ideas_db, update_history)  # noqa: E402
from .settings import (ICONS_DIR, icon_styles, read_alerts, read_carried, read_settings, read_translations)  # noqa: E402
from .calendar_glue import (calendar_data)  # noqa: E402
from .hq_exchange import (read_answers, read_proposal_marks, read_requests)  # noqa: E402
from .services import (read_services)  # noqa: E402
from .research import (read_research)  # noqa: E402
from .reports import (git_root, monthly_dir, read_reports, reports_dir)  # noqa: E402
from .digests import (digest_stamp, digest_view)  # noqa: E402
