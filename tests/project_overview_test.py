#!/usr/bin/env python3
"""Focused offline checks for project order, status, and assistant-facing files."""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pult import project_overview as overview  # noqa: E402
from pult import settings  # noqa: E402


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f" -- {detail}"))
    return bool(ok)


def main():
    passed = True
    temp = pathlib.Path(tempfile.mkdtemp(prefix="project-overview-test-"))
    saved = {name: getattr(overview, name) for name in ("SOURCE", "OVERVIEW", "HISTORY", "PENDING", "_build", "_atomic")}
    saved_settings_path = settings.SETTINGS
    source = temp / "projects.json"
    setting_file = temp / "settings.json"
    overview.SOURCE = source
    overview.OVERVIEW = temp / "project-overview.json"
    overview.HISTORY = temp / "project-overview-history.jsonl"
    overview.PENDING = temp / "project-overview-pending.json"
    overview._build = lambda: {}
    settings.SETTINGS = setting_file
    ids = ["a", "b", "c", "d", "e", "f", "g"]
    projects = [{"id": pid, "name": "Project " + pid, "group": "Synthetic", "status": "work" if i % 2 == 0 else "pause",
                 "stages": ["Plan", "Build"], "current": 0, "extra": {"keep": i}} for i, pid in enumerate(ids)]
    source.write_text(json.dumps({"projects": projects, "groups": ["Synthetic"], "history": [{"date": "2026-11-20", "project": "a", "text": "kept"}], "other": "preserved"}), encoding="utf-8")
    setting_file.write_text(json.dumps({"lang": "ru", "theme": "light", "ui": {"collapsed": ["all:tiles:0"], "project_order": ids}}), encoding="utf-8")
    try:
        cleaned = settings.clean_ui({"project_order": ["a", "a", "../x", 5, "b"], "collapsed": [], "summary_hidden": "", "seen": {}})
        passed &= check("settings clean_ui keeps only valid unique project IDs", cleaned.get("project_order") == ["a", "b"], repr(cleaned))
        target_order = ["g", "a", "b", "c", "d", "e", "f"]
        result, code = overview.apply_order({"project_id": "g", "previous_order": ids, "order": target_order})
        stored = settings.read_settings()
        snap = json.loads(overview.OVERVIEW.read_text(encoding="utf-8"))
        events = [json.loads(x) for x in overview.HISTORY.read_text(encoding="utf-8").splitlines()]
        passed &= check("order POST persists complete order and moves seventh into priority", code == 200 and result["ok"] and stored["ui"]["project_order"] == target_order and snap["focus_ids"] == target_order[:6], repr(result))
        passed &= check("order event records previous/new sequence and focus", len(events) == 1 and events[0]["kind"] == "order" and events[0]["changes"]["previous_order"] == ids and events[0]["changes"]["focus_ids"] == target_order[:6], repr(events))
        unchanged, code = overview.apply_order({"project_id": "g", "previous_order": target_order, "order": target_order})
        passed &= check("unchanged order creates no new event", code == 200 and unchanged.get("unchanged") and len(overview.HISTORY.read_text(encoding="utf-8").splitlines()) == 1, repr(unchanged))
        stale, code = overview.apply_order({"project_id": "g", "previous_order": ids, "order": ids})
        passed &= check("stale order returns conflict and current state", code == 409 and stale.get("conflict") and stale.get("order") == target_order, repr(stale))
        original = json.loads(source.read_text(encoding="utf-8"))
        old_status = next(p["status"] for p in original["projects"] if p["id"] == "g")
        changed, code = overview.apply_status({"id": "g", "previous_status": old_status, "status": "stop"})
        after = json.loads(source.read_text(encoding="utf-8"))
        project_g = next(p for p in after["projects"] if p["id"] == "g")
        snap = json.loads(overview.OVERVIEW.read_text(encoding="utf-8"))
        events = [json.loads(x) for x in overview.HISTORY.read_text(encoding="utf-8").splitlines()]
        passed &= check("status POST updates canonical project only and preserves position/other fields", code == 200 and changed["ok"] and project_g["status"] == "stop" and project_g["extra"] == {"keep": 6} and after["other"] == "preserved" and snap["focus_ids"] == target_order[:6] and snap["projects"][0]["status"] == "stop", repr(changed))
        passed &= check("status event records old and new codes", len(events) == 2 and events[-1]["kind"] == "status" and events[-1]["changes"] == {"previous_status": old_status, "status": "stop"}, repr(events[-1]))
        noop, code = overview.apply_status({"id": "g", "previous_status": "stop", "status": "stop"})
        conflict, conflict_code = overview.apply_status({"id": "g", "previous_status": old_status, "status": "pause"})
        passed &= check("same status is a no-op and stale status returns canonical status", code == 200 and noop.get("unchanged") and conflict_code == 409 and conflict.get("status") == "stop" and len(overview.HISTORY.read_text(encoding="utf-8").splitlines()) == 2, repr((noop, conflict)))
        event = {"schema_version": 1, "event_id": "recovery-1", "timestamp": "2026-11-21T00:00:00+00:00", "kind": "status", "project_id": "a", "changes": {"previous_status": "work", "status": "pause"}}
        pending = {"schema_version": 1, "event_id": "recovery-1", "timestamp": event["timestamp"], "kind": "status", "project_id": "a", "changes": event["changes"]}
        overview._atomic_json(overview.PENDING, pending)
        recovered = overview.recover_pending()
        count_before = len(overview.HISTORY.read_text(encoding="utf-8").splitlines())
        source_data = json.loads(source.read_text(encoding="utf-8"))
        source_data["projects"][0]["status"] = "pause"
        overview._atomic_json(source, source_data)
        overview._atomic_json(overview.PENDING, pending)
        recovered = overview.recover_pending()
        count_after = len(overview.HISTORY.read_text(encoding="utf-8").splitlines())
        overview._atomic_json(overview.PENDING, pending)
        overview.recover_pending()
        count_repeat = len(overview.HISTORY.read_text(encoding="utf-8").splitlines())
        passed &= check("pending applied status recovers snapshot and deduplicates event", recovered == "" and not overview.PENDING.exists() and count_after == count_before + 1 and count_repeat == count_after, (count_before, count_after, count_repeat))
        previous = json.loads(source.read_text(encoding="utf-8"))["projects"][0]["status"]
        canceled = dict(pending, event_id="recovery-cancel", changes={"previous_status": previous, "status": "stop"})
        overview._atomic_json(overview.PENDING, canceled)
        count_before = len(overview.HISTORY.read_text(encoding="utf-8").splitlines())
        overview.recover_pending()
        passed &= check("pending unapplied status cancels without event", not overview.PENDING.exists() and len(overview.HISTORY.read_text(encoding="utf-8").splitlines()) == count_before, "event count changed")
        bad = overview.apply_status({"id": "../a", "previous_status": "work", "status": "pause"})
        passed &= check("invalid status request is refused", bad[1] == 400 and not bad[0]["ok"], repr(bad))
        current_g = next(p["status"] for p in json.loads(source.read_text(encoding="utf-8"))["projects"] if p["id"] == "g")
        event_count = len(overview.HISTORY.read_text(encoding="utf-8").splitlines())
        real_atomic = overview._atomic
        def fail_source_write(path, payload):
            if path == source:
                raise OSError("injected synthetic write failure")
            return real_atomic(path, payload)
        overview._atomic = fail_source_write
        write_failed = False
        try:
            overview.apply_status({"id": "g", "previous_status": current_g, "status": "pause"})
        except OSError:
            write_failed = True
        finally:
            overview._atomic = real_atomic
        recovered_error = overview.recover_pending()
        final_source = json.loads(source.read_text(encoding="utf-8"))
        final_g = next(p["status"] for p in final_source["projects"] if p["id"] == "g")
        passed &= check("failed canonical write leaves source unchanged and recovery cancels pending without event",
                        write_failed and recovered_error == "" and final_g == current_g and not overview.PENDING.exists()
                        and len(overview.HISTORY.read_text(encoding="utf-8").splitlines()) == event_count,
                        repr((write_failed, recovered_error, final_g, event_count)))

        legacy_source = json.loads(source.read_text(encoding="utf-8"))
        legacy_values = ["work", "На паузе", " Работа ", "СТОП", "План", None, "unknown"]
        for project, value in zip(legacy_source["projects"], legacy_values):
            if value is None:
                project.pop("status", None)
            else:
                project["status"] = value
        overview._atomic_json(source, legacy_source)
        _, legacy_projects, legacy_ids = overview._projects()
        overview.write_snapshot(legacy_projects, target_order)
        legacy_snapshot = json.loads(overview.OVERVIEW.read_text(encoding="utf-8"))
        snapshot_by_id = {p["id"]: p["status"] for p in legacy_snapshot["projects"]}
        expected_statuses = {"a": "work", "b": "pause", "c": "work", "d": "stop", "e": "plan", "f": "pause", "g": "pause"}
        passed &= check("legacy and missing statuses read as canonical snapshot codes", legacy_ids == ids and snapshot_by_id == expected_statuses,
                        repr(snapshot_by_id))

        before_legacy = json.loads(source.read_text(encoding="utf-8"))
        stale_legacy, stale_legacy_code = overview.apply_status({"id": "b", "previous_status": "work", "status": "stop"})
        passed &= check("stale legacy status request conflicts with normalized current code", stale_legacy_code == 409 and stale_legacy.get("conflict") and stale_legacy.get("status") == "pause" and json.loads(source.read_text(encoding="utf-8")) == before_legacy,
                        repr(stale_legacy))
        legacy_changed, legacy_code = overview.apply_status({"id": "b", "previous_status": "pause", "status": "stop"})
        after_legacy = json.loads(source.read_text(encoding="utf-8"))
        before_by_id = {p["id"]: p for p in before_legacy["projects"]}
        after_by_id = {p["id"]: p for p in after_legacy["projects"]}
        untouched = all(after_by_id[pid] == before_by_id[pid] for pid in ids if pid != "b")
        passed &= check("changing one legacy project writes only its canonical status", legacy_code == 200 and legacy_changed["ok"] and after_by_id["b"]["status"] == "stop" and untouched and "status" not in after_by_id["f"] and after_legacy["other"] == before_legacy["other"],
                        repr((legacy_changed, after_by_id)))
        no_op_bytes = source.read_bytes()
        same_legacy, same_legacy_code = overview.apply_status({"id": "c", "previous_status": "work", "status": "work"})
        passed &= check("choosing a legacy project's current normalized status preserves its source bytes", same_legacy_code == 200 and same_legacy.get("unchanged") and source.read_bytes() == no_op_bytes,
                        repr(same_legacy))

        legacy_pending = {"schema_version": 1, "event_id": "legacy-recovery-once", "timestamp": event["timestamp"], "kind": "status", "project_id": "b",
                          "changes": {"previous_status": "pause", "status": "stop"}}
        recovery_events_before = len(overview.HISTORY.read_text(encoding="utf-8").splitlines())
        legacy_source = json.loads(source.read_text(encoding="utf-8"))
        next(p for p in legacy_source["projects"] if p["id"] == "b")["status"] = "СТОП"
        overview._atomic_json(source, legacy_source)
        overview._atomic_json(overview.PENDING, legacy_pending)
        recovered_legacy = overview.recover_pending()
        after_first_recovery = len(overview.HISTORY.read_text(encoding="utf-8").splitlines())
        overview._atomic_json(overview.PENDING, legacy_pending)
        overview.recover_pending()
        after_repeat_recovery = len(overview.HISTORY.read_text(encoding="utf-8").splitlines())
        passed &= check("pending status recovery recognizes legacy applied code and deduplicates event", recovered_legacy == "" and not overview.PENDING.exists() and after_first_recovery == recovery_events_before + 1 and after_repeat_recovery == after_first_recovery,
                        repr((recovered_legacy, recovery_events_before, after_first_recovery, after_repeat_recovery)))
    finally:
        for name, value in saved.items():
            setattr(overview, name, value)
        settings.SETTINGS = saved_settings_path
        import shutil
        shutil.rmtree(temp, ignore_errors=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
