# -*- coding: utf-8 -*-
"""Local ordering, status edits and assistant-facing overview files for the project cards."""
import datetime
import json
import os
import pathlib
import re
import threading
import uuid

from .config import HERE, SETTINGS, SOURCE

OVERVIEW = HERE / "project-overview.json"
HISTORY = HERE / "project-overview-history.jsonl"
PENDING = HERE / "project-overview-pending.json"
PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
STATUSES = ("work", "pause", "stop", "plan")
STATUS_ALIASES = {
    "в работе": "work", "работа": "work", "work": "work",
    "на паузе": "pause", "пауза": "pause", "pause": "pause",
    "остановлен": "stop", "стоп": "stop", "stop": "stop",
    "план": "plan", "plan": "plan",
}
FOCUS_SIZE = 6
PROJECT_LIMIT = 2000
_LOCK = threading.RLock()


def status_code(value):
    """Read current and legacy project statuses using the dashboard's canonical semantics."""
    return STATUS_ALIASES.get(str(value or "").strip().lower(), "pause")


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(temporary, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_json(path, value):
    _atomic(path, (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def _projects(source=None):
    source = _read_json(SOURCE) if source is None else source
    if not isinstance(source, dict) or not isinstance(source.get("projects"), list):
        raise ValueError("projects.json: нужен список projects")
    projects, ids = source["projects"], []
    for project in projects:
        if not isinstance(project, dict) or not isinstance(project.get("id"), str) or not PROJECT_ID.fullmatch(project["id"]):
            raise ValueError("projects.json: у проекта некорректный стабильный id")
        if project["id"] in ids:
            raise ValueError("projects.json: повторяется id проекта")
        ids.append(project["id"])
    if len(ids) > PROJECT_LIMIT:
        raise ValueError("projects.json: слишком много проектов")
    return source, projects, ids


def normalize_order(order, ids):
    """Keep valid saved IDs in order, discard removed/duplicate IDs, and append new source IDs."""
    known = set(ids)
    saved = order if isinstance(order, list) else []
    result, seen = [], set()
    for pid in saved:
        if isinstance(pid, str) and PROJECT_ID.fullmatch(pid) and pid in known and pid not in seen:
            result.append(pid)
            seen.add(pid)
    result.extend(pid for pid in ids if pid not in seen)
    return result


def _read_settings():
    from .settings import read_settings
    return read_settings()


def _current_order(ids, settings=None):
    settings = _read_settings() if settings is None else settings
    ui = settings.get("ui") if isinstance(settings, dict) else {}
    return normalize_order((ui or {}).get("project_order"), ids)


def _snapshot(projects, order):
    by_id = {project["id"]: project for project in projects}
    ordered = [by_id[pid] for pid in order]
    return {"schema_version": 1,
            "updated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "projects": [{"id": p["id"], "name": str(p.get("name") or p["id"]), "position": i + 1,
                          "status": status_code(p.get("status"))} for i, p in enumerate(ordered)],
            "focus_ids": order[:FOCUS_SIZE]}


def write_snapshot(projects=None, order=None):
    source, projects, ids = _projects() if projects is None else (None, projects, [p["id"] for p in projects])
    order = normalize_order(order if order is not None else _current_order(ids), ids)
    current = _snapshot(projects, order)
    try:
        old = _read_json(OVERVIEW)
    except (OSError, ValueError):
        old = None
    if isinstance(old, dict):
        # A normal rebuild does not change updated_at unless the represented state changed.
        old_core = {key: old.get(key) for key in ("schema_version", "projects", "focus_ids")}
        new_core = {key: current.get(key) for key in ("schema_version", "projects", "focus_ids")}
        if old_core == new_core and isinstance(old.get("updated_at"), str):
            return old
    _atomic_json(OVERVIEW, current)
    return current


def _read_history_ids():
    try:
        lines = HISTORY.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [], set()
    ids = set()
    for line in lines:
        try:
            event_id = json.loads(line).get("event_id")
            if isinstance(event_id, str):
                ids.add(event_id)
        except (ValueError, AttributeError):
            continue
    return lines, ids


def _append_once(event):
    lines, ids = _read_history_ids()
    if event["event_id"] in ids:
        return False
    lines.append(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
    _atomic(HISTORY, ("\n".join(lines) + "\n").encode("utf-8"))
    return True


def _state(source=None, settings=None):
    source, projects, ids = _projects(source)
    settings = _read_settings() if settings is None else settings
    return source, projects, ids, _current_order(ids, settings)


def _order_matches(value, expected, ids):
    return (isinstance(value, list) and len(value) == len(ids) and
            all(isinstance(v, str) and PROJECT_ID.fullmatch(v) for v in value) and
            len(set(value)) == len(value) and set(value) == set(ids) and value == expected)


def _focus(order):
    return order[:FOCUS_SIZE]


def _event(pending):
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    event = {"schema_version": 1, "event_id": pending["event_id"], "timestamp": pending.get("timestamp", now),
             "kind": pending["kind"], "project_id": pending["project_id"], "changes": pending["changes"]}
    return event


def _finish(pending):
    _, projects, ids, order = _state()
    write_snapshot(projects, order)
    added = _append_once(_event(pending))
    PENDING.unlink(missing_ok=True)
    return added


def recover_pending():
    """Complete a committed action once, cancel an unapplied action, or retain an ambiguous record."""
    with _LOCK:
        try:
            pending = _read_json(PENDING)
        except FileNotFoundError:
            return ""
        except (OSError, ValueError):
            return "project-overview-pending.json cannot be read"
        try:
            _, projects, ids, order = _state()
        except (OSError, ValueError) as exc:
            return f"project overview recovery: {exc}"
        changes = pending.get("changes") if isinstance(pending, dict) else None
        if not isinstance(changes, dict):
            return "project overview recovery: malformed pending record"
        pid = pending.get("project_id")
        by_id = {p["id"]: p for p in projects}
        applied = False
        unchanged = False
        if pending.get("kind") == "order" and _order_matches(changes.get("order"), changes.get("order"), ids):
            applied = order == changes.get("order")
            unchanged = order == changes.get("previous_order")
        elif pending.get("kind") == "status" and pid in by_id:
            previous = changes.get("previous_status")
            target = changes.get("status")
            if previous not in STATUSES or target not in STATUSES:
                return "project overview recovery: pending state conflicts with current projects"
            current = status_code(by_id[pid].get("status"))
            applied = current == target
            unchanged = current == previous
        else:
            return "project overview recovery: pending state conflicts with current projects"
        if applied:
            _finish(pending)
            return ""
        if unchanged:
            PENDING.unlink(missing_ok=True)
            return ""
        return "project overview recovery: pending state conflicts with current projects"


def _build():
    from .build import LAST_STAMPS, build, stamps
    data = build()
    LAST_STAMPS[0] = stamps()
    return data


def attach_to_build(data):
    """Normalize persisted IDs, expose a full order to the browser, and refresh the local snapshot."""
    if not isinstance(data, dict):
        return ""
    try:
        recovery_error = recover_pending()
        source, projects, ids = _projects()
        settings = _read_settings()
        ui = settings.setdefault("ui", {})
        stored = ui.get("project_order")
        order = normalize_order(stored, ids)
        if isinstance(stored, list) and order != stored:
            from .settings import SETTINGS_LOCK, write_settings
            with SETTINGS_LOCK:
                current = _read_settings()
                current["ui"]["project_order"] = order
                write_settings(current)
                settings = current
                ui = settings["ui"]
        ui["project_order"] = order
        data["settings"] = settings
        write_snapshot(projects, order)
        if recovery_error:
            data["project_overview_error"] = recovery_error
        return recovery_error
    except (OSError, ValueError, TypeError) as exc:
        message = f"project overview: {exc}"
        data["project_overview_error"] = message
        return message


def _pending(kind, project_id, changes):
    return {"schema_version": 1, "event_id": str(uuid.uuid4()), "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "kind": kind, "project_id": project_id, "changes": changes}


def apply_order(payload):
    from .build import SYNC_LOCK
    from .settings import SETTINGS_LOCK, read_settings, write_settings
    if not isinstance(payload, dict) or set(payload) != {"project_id", "previous_order", "order"}:
        return {"ok": False, "error": "Нужен объект project_id, previous_order, order"}, 400
    pid = payload.get("project_id")
    if not isinstance(pid, str) or not PROJECT_ID.fullmatch(pid):
        return {"ok": False, "error": "Некорректный project_id"}, 400
    with SYNC_LOCK, _LOCK:
        if recover_pending():
            return {"ok": False, "error": "Не удалось восстановить прошлую запись"}, 409
        try:
            source, projects, ids, current = _state()
        except (OSError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}, 409
        if pid not in ids:
            return {"ok": False, "error": "Проект не найден", "order": current}, 409
        if not _order_matches(payload.get("previous_order"), current, ids):
            return {"ok": False, "conflict": True, "error": "Порядок уже изменился", "order": current}, 409
        target = payload.get("order")
        if not _order_matches(target, target, ids):
            return {"ok": False, "error": "Нужен полный порядок проектов без повторов"}, 400
        if target == current:
            return {"ok": True, "unchanged": True, "order": current, "focus_ids": _focus(current)}, 200
        changes = {"previous_order": current, "order": target,
                   "previous_focus_ids": _focus(current), "focus_ids": _focus(target)}
        pending = _pending("order", pid, changes)
        _atomic_json(PENDING, pending)
        with SETTINGS_LOCK:
            settings = read_settings()
            settings["ui"]["project_order"] = target
            write_settings(settings)
        _finish(pending)
        data = _build()
        return {"ok": True, "order": target, "focus_ids": _focus(target),
                "snapshot": str(OVERVIEW.name), "rebuilt": data is not None}, 200


def apply_status(payload):
    from .build import SYNC_LOCK
    if not isinstance(payload, dict) or set(payload) != {"id", "previous_status", "status"}:
        return {"ok": False, "error": "Нужен объект id, previous_status, status"}, 400
    pid, previous, target = payload.get("id"), payload.get("previous_status"), payload.get("status")
    if not isinstance(pid, str) or not PROJECT_ID.fullmatch(pid) or previous not in STATUSES or target not in STATUSES:
        return {"ok": False, "error": "Некорректный проект или статус"}, 400
    with SYNC_LOCK, _LOCK:
        if recover_pending():
            return {"ok": False, "error": "Не удалось восстановить прошлую запись"}, 409
        try:
            source, projects, ids, order = _state()
        except (OSError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}, 409
        project = next((p for p in projects if p["id"] == pid), None)
        if project is None:
            return {"ok": False, "conflict": True, "error": "Проект не найден", "status": None}, 409
        current = status_code(project.get("status"))
        if current != previous:
            return {"ok": False, "conflict": True, "error": "Статус проекта уже изменился", "status": current}, 409
        if current == target:
            return {"ok": True, "unchanged": True, "status": current}, 200
        changes = {"previous_status": current, "status": target}
        pending = _pending("status", pid, changes)
        _atomic_json(PENDING, pending)
        project["status"] = target
        _atomic_json(SOURCE, source)
        _finish(pending)
        data = _build()
        return {"ok": True, "id": pid, "status": target, "snapshot": str(OVERVIEW.name),
                "rebuilt": data is not None}, 200
