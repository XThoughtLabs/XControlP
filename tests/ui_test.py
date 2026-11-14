# -*- coding: utf-8 -*-
"""Checks of the window's memory and of the HQ request kinds on the program's side (Python 3.10+, standard
library only).

    python -B tests/ui_test.py        exit 0: every check passes; exit 1: a check failed

Each check tries to break one rule: the window's memory in settings.json (folded cards, the summary hidden by
its cross, the answers already opened) keeps only checked values and survives other settings. Nothing is
written outside a temporary folder; no git command and no network call runs; data.js is not built.
"""
import json
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  - {detail}"))


def main():
    import pult.settings as settings
    built = []
    settings.build = lambda: built.append(1)          # no data.js in the repository folder
    settings.stamps = lambda: None

    folder = pathlib.Path(tempfile.mkdtemp(prefix="ui-test-"))
    try:
        settings.SETTINGS = folder / "settings.json"
        q = lambda **kw: {k: [v] for k, v in kw.items()}

        # V1: only checked values are kept: valid keys, deduplicated, at most 300; ids and sections checked.
        raw = {"collapsed": ["all:tiles:0", "all:tiles:0", "Bad Key", "x" * 81, 5, "h1a2b:s7:1"] + [f"k{i}:z:0" for i in range(400)],
               "summary_hidden": "<script>", "seen": {"summary": "request-2026-01-15-090000-summary", "evil": "x", "digest": "bad id!"}}
        got = settings.clean_ui(raw)
        check("V1 memory cleaned: valid unique keys, at most 300; bad ids and sections dropped",
              got["collapsed"][:2] == ["all:tiles:0", "h1a2b:s7:1"] and len(got["collapsed"]) == 300 and got["summary_hidden"] == ""
              and got["seen"] == {"summary": "request-2026-01-15-090000-summary"}, repr({k: (v[:3] if isinstance(v, list) else v) for k, v in got.items()}))

        # V2: the arrow: folding and unfolding a card is remembered; a bad key or value is refused and nothing is written.
        a = settings.save_ui(q(op="fold", key="all:tiles:0", on="1"))
        b = settings.save_ui(q(op="fold", key="digest:digest:2", on="1"))
        c = settings.save_ui(q(op="fold", key="all:tiles:0", on="0"))
        before = settings.SETTINGS.read_bytes()
        bad = [settings.save_ui(q(op="fold", key="Bad Key", on="1")), settings.save_ui(q(op="fold", key="all:x:0", on="2"))]
        check("V2 fold remembered and undone; bad key or value refused, file unchanged",
              a["ok"] and b["ok"] and c["ok"] and settings.read_settings()["ui"]["collapsed"] == ["digest:digest:2"]
              and not any(r["ok"] for r in bad) and settings.SETTINGS.read_bytes() == before, repr((c, bad)))

        # V3: the cross on the overview summary: its id is remembered; a bad id is refused.
        ok = settings.save_ui(q(op="hide-summary", id="request-2026-01-15-090000-summary"))
        empty = settings.save_ui(q(op="hide-summary", id="none:2026-01-15"))
        bad = settings.save_ui(q(op="hide-summary", id="../x y"))
        check("V3 summary hidden by id (also the empty day's id); bad id refused",
              ok["ok"] and empty["ok"] and not bad["ok"] and settings.read_settings()["ui"]["summary_hidden"] == "none:2026-01-15", repr(bad))

        # V4: an opened section puts out its green mark: per section; an unknown section or a bad id is refused.
        s1 = settings.save_ui(q(op="seen", section="summary", id="request-a-summary"))
        s2 = settings.save_ui(q(op="seen", section="proposals", id="request-b-proposals"))
        bad = [settings.save_ui(q(op="seen", section="calendar", id="x")), settings.save_ui(q(op="seen", section="digest", id=""))]
        other = settings.save_ui(q(op="nope"))
        check("V4 seen per section; unknown section, empty id and unknown action refused",
              s1["ok"] and s2["ok"] and settings.read_settings()["ui"]["seen"] == {"summary": "request-a-summary", "proposals": "request-b-proposals"}
              and not any(r["ok"] for r in bad) and not other["ok"], repr(bad))

        # V5: another setting (the language, the overview card switch) keeps the window's memory.
        settings.save_settings(q(lang="en"))
        settings.save_settings(q(summary_card="off"))
        now = settings.read_settings()
        check("V5 language and the card switch keep the memory", now["lang"] == "en" and now["summary_card"] == "off"
              and now["ui"]["collapsed"] == ["digest:digest:2"] and now["ui"]["seen"]["summary"] == "request-a-summary", repr(now))

        # V6: the card switch is on|off, on by default; a foreign value falls back to on and is refused on save.
        settings.SETTINGS.write_text(json.dumps({"summary_card": "maybe"}), encoding="utf-8")
        fallback = settings.read_settings()["summary_card"]
        refused = settings.save_settings(q(summary_card="maybe"))
        check("V6 card switch: on by default, only on|off", fallback == "on" and not refused["ok"]
              and settings.setting_choices()["summary_card"] == ("on", "off"), repr((fallback, refused)))
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
