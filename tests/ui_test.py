# -*- coding: utf-8 -*-
"""Checks of the window's memory and of the HQ request kinds on the program's side (Python 3.10+, standard
library only).

    python -B tests/ui_test.py        exit 0: every check passes; exit 1: a check failed

Each check tries to break one rule: the window's memory in settings.json (folded cards, the summary hidden by
its cross, the answers already opened) keeps only checked values and survives other settings; the three digest
request kinds are written, listed and answered like the first two, an unknown kind is refused. Nothing is
written outside a temporary folder; no git command and no network call runs; data.js is not built.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading

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

        # V1b: a key or an id with a trailing newline is not taken (the whole value must match).
        nl = settings.clean_ui({"collapsed": ["all:tiles:0\n"], "summary_hidden": "request-x\n", "seen": {"summary": "request-y\n"}})
        check("V1b trailing newline refused in keys and ids", nl == {"collapsed": [], "summary_hidden": "", "seen": {}}, repr(nl))

        # V7: what read_settings gives the window is cleaned: a bad memory in settings.json never reaches data.js.
        settings.SETTINGS.write_text(json.dumps({"ui": {"collapsed": ["ok:a:0", "<b>"], "summary_hidden": "x y", "seen": {"evil": "1"}}}), encoding="utf-8")
        cleaned = settings.read_settings()["ui"]
        check("V7 read_settings cleans the memory", cleaned == {"collapsed": ["ok:a:0"], "summary_hidden": "", "seen": {}}, repr(cleaned))
        settings.SETTINGS.unlink()

        # V8: two threads changing the memory at once lose nothing and never fail on the temporary file.
        errors = []

        def fold_many(prefix):
            for i in range(60):
                try:
                    r = settings.save_ui(q(op="fold", key=f"{prefix}:z:{i}", on="1"))
                    if not r["ok"]:
                        errors.append(r)
                except Exception as exc:
                    errors.append(repr(exc))
        threads = [threading.Thread(target=fold_many, args=(p,)) for p in ("aa", "bb")]
        [t.start() for t in threads]
        [t.join() for t in threads]
        kept = settings.read_settings()["ui"]["collapsed"]
        check("V8 parallel changes: all 120 folds kept, no error", not errors and len(kept) == 120, repr((len(kept), errors[:2])))
        settings.SETTINGS.unlink()

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

        # V4b: each digest tab is remembered by its own kind and survives a restart (read back from settings.json).
        s3 = settings.save_ui(q(op="seen", section="digest-interesting", id="request-i-digest-interesting"))
        s4 = settings.save_ui(q(op="seen", section="digest-useful", id="request-u-digest-useful"))
        kept = settings.read_settings()["ui"]["seen"]
        check("V4b the digest tabs remembered per kind after a restart",
              s3["ok"] and s4["ok"] and kept == {"summary": "request-a-summary", "proposals": "request-b-proposals",
                                                 "digest-interesting": "request-i-digest-interesting", "digest-useful": "request-u-digest-useful"}, repr(kept))

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

        # R1-R4: the HQ request kinds (XCP-25 C).
        import pult.hq_exchange as hq
        from pult.config import REQUEST_KINDS
        hq.build = lambda: None
        hq.stamps = lambda: None
        hq.REQUESTS_DIR = folder / "requests"
        import datetime as real_datetime
        import types

        class Fixed(real_datetime.datetime):           # one second for both writes: the second file must get -2
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 1, 15, 10, 0, 0)
        hq.datetime = types.SimpleNamespace(datetime=Fixed, date=real_datetime.date)
        three = ("digest-interesting", "digest-useful", "digest-ideas")
        check("R1 request kinds: the two first and the three digest kinds", REQUEST_KINDS == ("summary", "proposals") + three, repr(REQUEST_KINDS))

        lang = {"ru": "т", "en": "t", "he": "ת"}
        answer = lambda kind, **kw: dict({"format": "pult-answer", "version": 1, "kind": kind, "written": "2026-01-15T10:00", "title": lang}, **kw)
        problems = {k: hq.check_answer(answer(k, summary=lang, blocks=[], proposals=[{"id": "p1", "text": lang, "why": lang, "project": "web"}] if k == "digest-ideas" else []))
                    for k in REQUEST_KINDS}
        unknown = hq.check_answer(answer("digest-everything"))
        check("R2 answers of every kind accepted; an unknown kind refused with the list", all(v == "" for v in problems.values())
              and "digest-useful" in unknown, repr((problems, unknown)))

        snap = {"kind": "digest-ideas", "period": {"name": "week", "from": "2026-01-09", "to": "2026-01-15"},
                "items": [{"id": "a", "date": "2026-01-15", "title": "т", "marks": {"useful": True}}], "projects": [{"id": "web"}]}
        w1 = hq.write_request(q(kind="digest-ideas"), json.dumps(snap).encode("utf-8"))
        w2 = hq.write_request(q(kind="digest-ideas"), json.dumps(snap).encode("utf-8"))
        w3 = hq.write_request(q(kind="digest-everything"), b"{}")
        saved = json.loads((hq.REQUESTS_DIR / (w1["id"] + ".json")).read_text(encoding="utf-8")) if w1.get("ok") else {}
        check("R3 digest request written with its snapshot; same second gets -2; unknown kind refused",
              w1["ok"] and w2["ok"] and w2["id"] == w1["id"] + "-2" and saved.get("kind") == "digest-ideas" and saved.get("snapshot") == snap
              and not w3["ok"], repr((w1, w2, w3)))

        hq.datetime = real_datetime
        listed = hq.read_requests([{"data": {"request": w1["id"]}}])
        by = {r["id"]: r for r in listed}
        check("R4 requests listed with their kind (also with -2) and whether answered",
              by[w1["id"]]["kind"] == "digest-ideas" and by[w2["id"]]["kind"] == "digest-ideas" and by[w1["id"]]["answered"] is True
              and by[w2["id"]]["answered"] is False and by[w1["id"]]["created"].startswith(w1["id"][8:18]), repr(listed))

        # R5: the HQ helper tools/answer_check.py accepts a digest answer with the program's own rule.
        good = folder / "answer-good.json"
        good.write_text(json.dumps(answer("digest-useful", summary=lang, blocks=[])), encoding="utf-8")
        bad = folder / "answer-bad.json"
        bad.write_text(json.dumps(answer("digest-everything")), encoding="utf-8")
        run = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "answer_check.py"), str(ROOT / "XControlP.pyw"), str(good), str(bad)],
                             capture_output=True, text=True, encoding="utf-8")
        check("R5 answer_check: digest answer OK, unknown kind BAD", run.returncode == 1 and "OK   " + str(good) in run.stdout
              and "BAD  " + str(bad) in run.stdout, run.stdout + run.stderr)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
