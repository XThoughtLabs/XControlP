# -*- coding: utf-8 -*-
"""Проверки плана дня (day_store.py, day.py). Работают во временной папке; day.db Пульта не трогают.

  python day_test.py            проекты-образцы (alpha, beta, gamma) пишет сам во временную папку; данные Пульта не нужны
Каждое правило базы проверяется попыткой его нарушить: проверка, которая не может провалиться, не считается.
"""
import datetime
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import day_store as ds  # noqa: E402

PASSED, FAILED = [], []

# Проекты-образцы: проверки не зависят от данных пользователя. У beta текущий этап не первый (K5),
# у всех проектов есть этапы (K11 и «завершить этап»). auto.json не нужен: load_projects обходится без него.
FIXTURE = {
    "updated": "", "focus": "", "ideas_files": [], "groups": [],
    "projects": [
        {"id": "alpha", "name": "Альфа", "group": "", "status": "в работе", "stages": ["Урок 1", "Урок 2", "Урок 3"], "current": 0},
        {"id": "beta", "name": "Бета", "group": "", "status": "в работе", "stages": ["Этап 1", "Этап 2", "Этап 3", "Этап 4"], "current": 2},
        {"id": "gamma", "name": "Гамма", "group": "", "status": "план", "stages": ["Черновик", "Готово"], "current": 1},
    ],
    "history": [],
}


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  — {detail}"))


def refused(name, fn, *words):
    try:
        fn()
    except (ds.DayError, sqlite3.IntegrityError) as exc:
        text = str(exc)
        check(name, all(w in text for w in words), f"отказ, но другой: {text}")
        return
    check(name, False, "не отказала")


def fresh():
    folder = pathlib.Path(tempfile.mkdtemp(prefix="day-test-"))
    (folder / "projects.json").write_text(json.dumps(FIXTURE, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy(HERE / "day_store.py", folder / "day_store.py")
    shutil.copy(HERE / "day.py", folder / "day.py")
    return folder, ds.Store(folder)


def raw(store):
    conn = ds.connect(store.db)
    return conn


def main():
    folder, store = fresh()
    today = datetime.date.today()
    T = today.isoformat()
    T1 = (today + datetime.timedelta(days=1)).isoformat()
    Y = (today - datetime.timedelta(days=1)).isoformat()
    P = ds.load_projects(folder)
    pid = "alpha"            # «продвинуться»
    sid = "beta"             # «завершить этап»: текущий этап не первый

    # --- схема, настройки
    v = store.view(T)
    conn = raw(store)
    check("K1 схема записана в файл", conn.execute("PRAGMA user_version").fetchone()[0] == ds.SCHEMA_VERSION)
    check("K2 журнал TRUNCATE и полная запись", conn.execute("PRAGMA journal_mode").fetchone()[0] == "truncate"
          and conn.execute("PRAGMA synchronous").fetchone()[0] == 2)
    check("K3 пустой день читается", v["ok"] and v["items"] == [] and v["note"] == "")

    # --- добавление: три вида
    r = store.apply([{"op": "add", "day": T, "kind": "advance", "project": pid, "amount": "1 урок", "priority": "high"},
                     {"op": "add", "day": T, "kind": "stage", "project": sid},
                     {"op": "add", "day": T, "kind": "task", "title": "Своя   задача  ", "priority": "low"}])
    a, b, c = (x["id"] for x in r)
    items = store.view(T)["items"]
    check("K4 три вида задач добавлены по порядку", [i["id"] for i in items] == [a, b, c])
    check("K5 этап по умолчанию — текущий этап проекта", items[1]["stage_index"] == P[sid]["current"]
          and items[1]["stage_name"] == P[sid]["stages"][P[sid]["current"]])
    check("K6 пробелы в тексте сжаты", items[2]["title"] == "Своя задача")
    check("K7 кто добавил записан", all(i["added_by"] == "pult" for i in items))
    check("K8 day.json написан и в нём эти задачи", len(json.loads(store.export_path.read_text(encoding="utf-8"))["days"][T]["items"]) == 3)

    # --- отказы при добавлении
    refused("K9 нет проекта — отказ", lambda: store.apply([{"op": "add", "day": T, "kind": "advance", "project": "нет-такого", "amount": "1"}]), "нет проекта")
    refused("K10 «продвинуться» без «насколько» — отказ", lambda: store.apply([{"op": "add", "day": T, "kind": "advance", "project": pid}]), "насколько")
    refused("K11 этап вне списка — отказ", lambda: store.apply([{"op": "add", "day": T, "kind": "stage", "project": sid, "stage": 999}]), "этап")
    refused("K12 несуществующая дата — отказ", lambda: store.apply([{"op": "add", "day": "2026-02-30", "kind": "task", "title": "x"}]), "даты нет")
    refused("K13 неизвестный вид — отказ", lambda: store.apply([{"op": "add", "day": T, "kind": "что-то", "title": "x"}]), "вид задачи")
    refused("K14 пустая своя задача — отказ", lambda: store.apply([{"op": "add", "day": T, "kind": "task", "title": "   "}]), "не задано")
    n_before = len(store.view(T)["items"])
    refused("K15 запрос с одной ошибкой не меняет ничего (всё или ничего)",
            lambda: store.apply([{"op": "add", "day": T, "kind": "task", "title": "хорошая"}, {"op": "add", "day": T, "kind": "task"}]), "не задано")
    check("K15b после отказа задач столько же", len(store.view(T)["items"]) == n_before)

    # --- статусы, заметки, приоритет, правка
    store.apply([{"op": "status", "id": a, "status": "done", "note": "урок 3.2"}, {"op": "priority", "id": c, "priority": "high"},
                 {"op": "edit", "id": a, "amount": "2 урока"}])
    items = {i["id"]: i for i in store.view(T)["items"]}
    check("K16 статус, заметка, приоритет", items[a]["status"] == "done" and items[a]["note"] == "урок 3.2" and items[c]["priority"] == "high")
    check("K17 правка «насколько» меняет и текст", items[a]["amount"] == "2 урока" and items[a]["title"] == "2 урока")
    refused("K18 «перенесено» руками не ставится", lambda: store.apply([{"op": "status", "id": b, "status": "moved"}]), "статус")
    refused("K19 сделанную не перенести", lambda: store.apply([{"op": "carry", "id": a}]), "незаконченную")

    # --- порядок
    store.apply([{"op": "order", "day": T, "ids": [c, a, b]}])
    check("K20 новый порядок", [i["id"] for i in store.view(T)["items"]] == [c, a, b])
    refused("K21 порядок с чужим набором — отказ", lambda: store.apply([{"op": "order", "day": T, "ids": [c, a]}]), "устарел")

    # --- на завтра
    res = store.apply([{"op": "carry", "id": b}])[0]
    items = {i["id"]: i for i in store.view(T)["items"]}
    tomorrow = store.view(T1)["items"]
    check("K22 «на завтра»: старая — перенесено, новая — завтра", items[b]["status"] == "moved" and items[b]["moved_to"] == res["new"]
          and items[b]["moved_to_day"] == T1 and tomorrow[0]["moved_from"] == b and tomorrow[0]["status"] == "planned")
    refused("K23 перенесённую не перенести второй раз", lambda: store.apply([{"op": "carry", "id": b}]), "незаконченную")
    refused("K24 у перенесённой статус не меняется", lambda: store.apply([{"op": "status", "id": b, "status": "done"}]), "перенесена")
    y = store.apply([{"op": "add", "day": Y, "kind": "task", "title": "вчерашняя"}])[0]["id"]
    res = store.apply([{"op": "carry", "id": y}])[0]
    check("K25 вчерашняя «на завтра» попадает на сегодня", res["to"] == T)
    refused("K26 перенос назад — отказ", lambda: store.apply([{"op": "carry", "id": c, "to": Y}]), "более поздний")

    # --- убрать и вернуть
    store.apply([{"op": "remove", "id": c}])
    check("K27 убранная остаётся в базе со статусом «убрано»", {i["id"]: i for i in store.view(T)["items"]}[c]["status"] == "removed")
    store.apply([{"op": "restore", "id": c}])
    check("K28 убранную можно вернуть", {i["id"]: i for i in store.view(T)["items"]}[c]["status"] == "planned")
    store.apply([{"op": "remove", "id": a}, {"op": "restore", "id": a}])
    check("K28b возвращается прежний статус («сделано» остаётся «сделано»)", {i["id"]: i for i in store.view(T)["items"]}[a]["status"] == "done")
    refused("K28c вернуть можно только убранную", lambda: store.apply([{"op": "restore", "id": a}]), "только убранную")

    # --- план целиком
    store.apply([{"op": "plan", "day": T1, "replace": True, "items": [{"kind": "advance", "project": pid, "amount": "1 урок"},
                                                                      {"kind": "task", "title": "SQL: урок"}]}])
    day1 = store.view(T1)["items"]
    check("K29 план с заменой: не начатые задачи дня убраны, новые добавлены",
          [i["status"] for i in day1] == ["removed", "planned", "planned"])

    # --- заметка дня, итоги
    store.apply([{"op": "day_note", "day": T, "note": "хороший день"}, {"op": "day_note", "day": T, "note": "хороший день!"}])
    v = store.view(T)
    s = {x["day"]: x for x in v["summary"]}
    check("K30 заметка дня (второй раз — обновление)", v["note"] == "хороший день!")
    check("K31 итог дня: всего без убранных, процент", s[T]["total"] == 4 and s[T]["counts"]["done"] == 1 and s[T]["percent"] == 25,
          json.dumps(s.get(T), ensure_ascii=False))

    # --- база сама отказывает (мимо программы)
    conn = raw(store)
    refused("K32 удалить задачу нельзя", lambda: conn.execute("DELETE FROM items WHERE id = ?", (a,)), "не удаляются")
    refused("K33 INSERT OR REPLACE не обходит запрет удаления",
            lambda: conn.execute("INSERT OR REPLACE INTO items SELECT * FROM items WHERE id = ?", (a,)), "не удаляются")
    refused("K34 журнал не правится", lambda: conn.execute("UPDATE item_log SET new = 'x'"), "только дописывается")
    refused("K35 журнал не стирается", lambda: conn.execute("DELETE FROM item_log"), "только дописывается")
    refused("K36 день задачи не меняется", lambda: conn.execute("UPDATE items SET day = ? WHERE id = ?", (T1, a)), "не меняются")
    refused("K37 неверный статус — CHECK", lambda: conn.execute("UPDATE items SET status = 'готово' WHERE id = ?", (a,)), "CHECK")
    refused("K38 «перенесено» без ссылки — CHECK", lambda: conn.execute("UPDATE items SET status = 'moved' WHERE id = ?", (c,)), "CHECK")
    refused("K39 ссылка на несуществующую задачу — внешний ключ",
            lambda: conn.execute("UPDATE items SET status = 'moved', moved_to = ? WHERE id = ?", ("f" * 32, c)), "FOREIGN KEY")
    refused("K40 «этап» без номера этапа — CHECK", lambda: conn.execute(
        "INSERT INTO items (id, day, position, priority, kind, project_id, project_name, title, status, note, added_by, created_at, updated_at) "
        "VALUES (?, ?, 0, 'normal', 'stage', 'x', 'x', 't', 'planned', '', 'pult', ?, ?)", ("e" * 32, T, ds.now_text(), ds.now_text())), "CHECK")
    refused("K41 дата 2026-13-01 — CHECK", lambda: conn.execute("INSERT INTO day_notes (day, note, updated_at) VALUES ('2026-13-01', '', ?)",
                                                                (ds.now_text(),)), "CHECK")
    refused("K42b заметку дня не удалить", lambda: conn.execute("DELETE FROM day_notes"), "не удаляются")
    log = conn.execute("SELECT action, count(*) FROM item_log GROUP BY action").fetchall()
    check("K43 журнал записал добавления, статусы, перенос, порядок", {r[0] for r in log} >= {"add", "status", "carry", "order", "note", "priority", "edit"},
          str([tuple(r) for r in log]))
    check("K44 целостность базы", conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and not conn.execute("PRAGMA foreign_key_check").fetchall())
    conn.close()

    # --- резерв
    copies = list(store.backups.glob("day *.db"))
    check("K45 резерв за день сделан один раз", len(copies) == 1, str(copies))
    bk = sqlite3.connect(str(copies[0]))
    check("K46 резерв — настоящая база, открывается", bk.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
    bk.close()

    # --- версия схемы новее — не открывать
    conn = sqlite3.connect(str(store.db)); conn.execute("PRAGMA user_version = 9"); conn.close()
    refused("K47 файл более новой версии не открывается", lambda: ds.Store(folder).view(T), "более новой версией")
    conn = sqlite3.connect(str(store.db)); conn.execute(f"PRAGMA user_version = {ds.SCHEMA_VERSION}"); conn.close()

    # --- запросы Claude через day.py и day-inbox
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    run = lambda *args: subprocess.run([sys.executable, str(folder / "day.py")] + list(args), capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(folder))
    out = run("add", "--day", T, "--project", pid, "--amount", "1 урок", "--priority", "high")
    check("K48 day.py add пишет запрос, базу не трогает", out.returncode == 0 and len(list(store.inbox.glob("*.json"))) == 1, out.stderr + out.stdout)
    new_id = [w for w in out.stdout.split() if len(w) == 32][0]
    out2 = run("status", new_id, "done")
    check("K49 day.py видит ещё не применённую задачу (проверка поверх ждущих запросов)", out2.returncode == 0, out2.stderr + out2.stdout)
    bad = run("add", "--day", T, "--project", "нет-такого", "--amount", "1")
    check("K50 day.py: ошибка видна сразу, запрос не отправлен", bad.returncode != 0 and "нет проекта" in (bad.stderr + bad.stdout)
          and len(list(store.inbox.glob("*.json"))) == 2)
    (store.inbox / "20990101-000000-broken.json").write_text("{не json", encoding="utf-8")
    os.utime(store.inbox / "20990101-000000-broken.json", (time.time() - 60, time.time() - 60))
    (store.inbox / "20990101-000001-badop.json").write_text(json.dumps({"format": 1, "ops": [{"op": "status", "id": a, "status": "x"}]}), encoding="utf-8")
    (store.inbox / "20990101-000002-young.json").write_text("{", encoding="utf-8")
    done = store.process_inbox()
    check("K51 два запроса day.py применены по порядку", [d["ok"] for d in done[:2]] == [True, True], json.dumps(done, ensure_ascii=False)[:400])
    items = {i["id"]: i for i in store.view(T)["items"]}
    check("K52 задача от Claude добавлена и отмечена «сделано»", items[new_id]["status"] == "done" and items[new_id]["added_by"] == "claude")
    check("K53 сломанный и неверный запросы не приняты, итог с ошибкой", [d["ok"] for d in done[2:]] == [False, False])
    check("K54 недописанный свежий запрос ждёт", (store.inbox / "20990101-000002-young.json").is_file())
    check("K55 итоги лежат в applied", len(list(store.applied.glob("*.result.json"))) == 4)
    first = sorted(store.applied.glob("2*.json"))[0]
    shutil.copy(first, store.inbox / first.name)
    again = store.process_inbox()
    check("K56 повтор того же запроса не применяется второй раз", again and again[0].get("repeat") and
          sum(1 for i in store.view(T)["items"] if i["added_by"] == "claude") == 1, json.dumps(again, ensure_ascii=False)[:300])
    conn = raw(store)
    refused("K42 запрос в журнале не правится", lambda: conn.execute("UPDATE requests SET ok = 1"), "только дописывается")
    refused("K42c запрос из журнала не стереть", lambda: conn.execute("DELETE FROM requests"), "только дописывается")
    conn.close()
    res = run("result")
    check("K57 day.py result показывает итоги", "принят" in res.stdout and "НЕ принят" in res.stdout, res.stdout + res.stderr)
    shown = run("show", "--day", T)
    check("K58 day.py show читает day.json", new_id in shown.stdout and "(Claude)" in shown.stdout, shown.stdout + shown.stderr)

    # --- итоги дней (схема v2)
    store = ds.Store(folder)
    refused("K60 оценка 0 — отказ", lambda: store.apply([{"op": "close_day", "day": T, "rating": 0}]), "от 1 до 10")
    refused("K61 оценка 11 — отказ", lambda: store.apply([{"op": "close_day", "day": T, "rating": 11}]), "от 1 до 10")
    refused("K62 оценка 7.5 — отказ", lambda: store.apply([{"op": "close_day", "day": T, "rating": 7.5}]), "от 1 до 10")
    store.apply([{"op": "close_day", "day": T, "rating": 7, "note": "нормальный день"}])
    v = store.view(T)
    check("K63 день закрыт с оценкой и итогом", v["close"]["rating"] == 7 and v["close"]["closed"] == 1 and v["note"] == "нормальный день")
    store.apply([{"op": "close_day", "day": T, "rating": 8}])
    store.apply([{"op": "reopen_day", "day": T}])
    s = {x["day"]: x for x in store.review(Y, T1)["days"]}
    check("K64 переоценка и «открыть снова»: оценка 8, день открыт", s[T]["rating"] == 8 and not s[T]["closed"])
    refused("K65 открыть незакрытый — отказ", lambda: store.apply([{"op": "reopen_day", "day": T}]), "не закрыт")
    conn = raw(store)
    log = [tuple(r) for r in conn.execute("SELECT action, old, new FROM day_log WHERE day = ? ORDER BY n", (T,)).fetchall()]
    check("K66 журнал итогов: закрыт → переоценён → открыт", log == [("close", None, "7"), ("rate", "7", "8"), ("reopen", "8", None)], log)
    refused("K67 журнал итогов не правится", lambda: conn.execute("UPDATE day_log SET new = '1'"), "только дописывается")
    refused("K68 итоги дня не удаляются", lambda: conn.execute("DELETE FROM day_close"), "не удаляются")
    refused("K69 оценка 0 мимо программы — CHECK", lambda: conn.execute("UPDATE day_close SET rating = 0"), "CHECK")
    conn.close()
    d2 = (today + datetime.timedelta(days=5)).isoformat()
    store.apply([{"op": "add", "day": d2, "kind": "task", "title": "a"}, {"op": "add", "day": d2, "kind": "task", "title": "b"}])
    first_id = store.view(d2)["items"][0]["id"]
    store.apply([{"op": "status", "id": first_id, "status": "done"}, {"op": "carry_open", "day": d2}])
    left = [i["status"] for i in store.view(d2)["items"]]
    nxt = store.view((today + datetime.timedelta(days=6)).isoformat())["items"]
    check("K70 «все незаконченные на завтра»: сделанная остаётся, остальные переносятся", left == ["done", "moved"] and len(nxt) == 1 and nxt[0]["title"] == "b")
    out = run("close", "--day", T, "--rating", "6")
    check("K71 day.py close пишет запрос (проверен заранее)", out.returncode == 0, out.stderr + out.stdout)
    bad = run("close", "--day", T, "--rating", "12")
    check("K72 day.py close с оценкой 12 — не отправлен", bad.returncode != 0 and "от 1 до 10" in (bad.stderr + bad.stdout))

    # --- переход со схемы v1 на v2 с данными и резервом
    f2 = pathlib.Path(tempfile.mkdtemp(prefix="day-mig-"))
    shutil.copy(folder / "projects.json", f2 / "projects.json")
    c1 = sqlite3.connect(str(f2 / "day.db"), isolation_level=None)
    c1.executescript("BEGIN;" + ds.MIGRATIONS[0] + "PRAGMA user_version = 1; COMMIT;")
    c1.execute("INSERT INTO items (id, day, position, priority, kind, title, status, note, added_by, created_at, updated_at) "
               "VALUES (?, ?, 0, 'normal', 'task', 'старая задача', 'done', '', 'pult', ?, ?)", ("a" * 32, T, ds.now_text(), ds.now_text()))
    c1.close()
    s2 = ds.Store(f2)
    v2 = s2.view(T)
    conn = sqlite3.connect(str(f2 / "day.db"))
    check("K73 файл v1 дошагал до v2, данные целы", conn.execute("PRAGMA user_version").fetchone()[0] == 2 and v2["items"][0]["title"] == "старая задача")
    conn.close()
    check("K74 перед переходом сделан резерв «before-schema-v2»", any("before-schema-v2" in x.name for x in (f2 / "day-plan-backups").glob("*.db")))
    shutil.rmtree(f2, ignore_errors=True)

    print(f"\nПройдено {len(PASSED)}, не пройдено {len(FAILED)}" + (": " + ", ".join(FAILED) if FAILED else ""))
    shutil.rmtree(folder, ignore_errors=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
