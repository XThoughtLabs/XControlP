# -*- coding: utf-8 -*-
"""План дня Пульта — для Claude (и для любого скрипта). Базу day.db этот скрипт НЕ открывает.

Читает:  day.json (копия, которую пишет Пульт), projects.json и auto.json (проекты и этапы).
Пишет:   только файлы запросов в day-inbox/. Пульт применяет их сам (окно открыто — в течение ~10 секунд;
         закрыто — при следующем открытии) и кладёт итог в day-inbox/applied/<имя>.result.json.
Каждый запрос проверяется здесь заранее тем же кодом, что и в Пульте (day_store.py), чтобы ошибка была видна сразу.

  python day.py projects                                  проекты, их номера и этапы (с какого этапа можно планировать)
  python day.py show [--day 2026-10-07]                   план дня из day.json + запросы, которые ещё ждут Пульт
  python day.py add --day D --project english --amount "1 урок" [--priority high|normal|low] [--note ТЕКСТ]
  python day.py add --day D --project website --stage [N]               завершить этап N (номер как на Пульте, с 1; без N — текущий)
  python day.py add --day D --task "Позвонить в банк" [--project ID]
  python day.py plan --day D --file план.json [--replace]   день целиком: список задач JSON (поля как у add:
                                                          kind stage|advance|task, project, stage — номер как на Пульте, с 1, amount, title, priority, note)
  python day.py status ID done|partial|not_done|active|planned|removed [--note ТЕКСТ]
  python day.py note ID ТЕКСТ    priority ID high|normal|low    carry ID [--to D]    restore ID
  python day.py edit ID [--stage N] [--amount ТЕКСТ] [--title ТЕКСТ]   поправить этап (с 1), «насколько» или текст
  python day.py order --day D ID ID ID …                  новый порядок всех задач дня
  python day.py day-note --day D ТЕКСТ                    заметка (итог) дня
  python day.py close --day D --rating 1..10 [--note ТЕКСТ]   закрыть день с оценкой (вкладка «Итоги дней»)
  python day.py reopen --day D    carry-open --day D      открыть день снова · все незаконченные — на следующий день
  python day.py result [ИМЯ]                              итог запроса (без имени — последние)
Номер задачи (ID) — 32 знака, его печатает add и show. День по умолчанию — сегодня по времени Израиля.
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import time
import uuid

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import day_store  # noqa: E402

INBOX = HERE / "day-inbox"
APPLIED = INBOX / "applied"
EXPORT = HERE / "day.json"
MARK = {"planned": "○", "active": "▶", "done": "✓", "partial": "◐", "not_done": "✗", "moved": "→", "removed": "–"}
PRIO = {"high": "!", "normal": " ", "low": "·"}


def israel_today():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Asia/Jerusalem")).date().isoformat()
    except Exception:
        return datetime.date.today().isoformat()


def read_export():
    try:
        return json.loads(EXPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def projects():
    return day_store.load_projects(HERE)


COLUMNS = ("id", "day", "position", "priority", "kind", "project_id", "project_name", "stage_index", "stage_name", "amount",
           "title", "status", "note", "moved_to", "moved_from", "added_by", "created_at", "updated_at")


def dry_run(ops):
    """Проверить запрос тем же кодом, что и Пульт, на копии в памяти: задачи из day.json,
    поверх — запросы, которые ещё ждут Пульт, и только потом новый запрос. day.db не открывается."""
    store = day_store.Store(HERE, projects=projects)
    p = projects()
    conn = day_store.sqlite3.connect(":memory:", isolation_level=None)
    conn.row_factory = day_store.sqlite3.Row
    try:
        for sql in day_store.MIGRATIONS:
            conn.executescript(sql)
        conn.execute("PRAGMA foreign_keys = OFF")          # в копии могут быть ссылки на дни старше day.json
        for day in ((read_export() or {}).get("days") or {}).values():
            for it in day.get("items", []):
                conn.execute(f"INSERT INTO items ({', '.join(COLUMNS)}) VALUES ({', '.join('?' for _ in COLUMNS)})",
                             [it.get(c) for c in COLUMNS])
        conn.execute("PRAGMA recursive_triggers = ON")
        for waiting in sorted(INBOX.glob("*.json")) if INBOX.is_dir() else []:
            try:
                earlier = json.loads(waiting.read_text(encoding="utf-8-sig")).get("ops") or []
            except (ValueError, OSError, AttributeError):
                continue
            conn.execute("SAVEPOINT earlier")
            try:
                for op in earlier:
                    store.one(conn, op, "claude", p)
                conn.execute("RELEASE earlier")
            except (TypeError, AttributeError, day_store.DayError, day_store.sqlite3.Error):
                conn.execute("ROLLBACK TO earlier")
                conn.execute("RELEASE earlier")
        conn.execute("SAVEPOINT new")
        try:
            return [store.one(conn, op, "claude", p) for op in ops]
        except day_store.sqlite3.IntegrityError as exc:
            raise day_store.DayError(f"база не приняла бы изменение: {exc}")
    finally:
        conn.close()


def send(ops, comment=""):
    try:
        checked = dry_run(ops)
    except day_store.DayError as exc:
        sys.exit(f"Не отправлено — ошибка в запросе: {exc}")
    INBOX.mkdir(exist_ok=True)
    # Пульт применяет запросы по порядку имён: имя — время с микросекундами, и всегда позже ждущих запросов.
    last = max((p.name for p in INBOX.glob("*.json")), default="")
    for _ in range(5):
        now = datetime.datetime.now()
        name = now.strftime("%Y%m%d-%H%M%S-") + f"{now.microsecond:06d}-" + uuid.uuid4().hex[:6] + ".json"
        if name > last:
            break
        time.sleep(0.002)
    else:                                       # ждущий запрос «из будущего» (часы) — встать сразу за ним
        name = last[:-5][:100] + "_" + uuid.uuid4().hex[:6] + ".json"
    body = {"format": day_store.FORMAT, "by": "claude", "comment": comment, "ops": ops}
    temporary = INBOX / (name[:-5] + ".tmp")
    temporary.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, INBOX / name)
    print(f"Запрос {name} отправлен Пульту ({len(ops)} действ.).")
    for r in checked:
        if r.get("op") == "add":
            print(f"  + {r['id']}  {r['day']}  {r['title']}")
        elif r.get("op") == "plan":
            print(f"  план {r['day']}: задач {len(r['added'])}" + (f", убрано {len(r['removed'])}" if r["removed"] else ""))
    print("Пульт применит его сам: окно открыто — в течение ~10 секунд, закрыто — при следующем открытии.")
    print(f"Проверить: python day.py result {name}")


def add_op(a):
    op = {"op": "add", "day": a.day or israel_today(), "priority": a.priority}
    if a.project:
        op["project"] = a.project
    if a.task:
        op.update(kind="task", title=a.task)
    elif a.amount:
        op.update(kind="advance", amount=a.amount)
    elif a.stage is not None:
        op["kind"] = "stage"
        if a.stage != "current":
            op["stage"] = int(a.stage) - 1          # на Пульте этапы считаются с 1, в базе — с 0
    else:
        sys.exit("Нужно одно из: --stage [N], --amount ТЕКСТ, --task ТЕКСТ")
    if a.title and op["kind"] != "task":
        op["title"] = a.title
    if a.note:
        op["note"] = a.note
    op["id"] = uuid.uuid4().hex
    return op


def cmd_projects(a):
    for p in projects().values():
        st = p["stages"]
        cur = st[p["current"]] if st else "—"
        print(f"{p['id']:<20} {p['name']}  [{p['group']}; {p['status']}]")
        print(f"{'':<20} сейчас этап {p['current'] + 1}: {cur}")
        if a.all:
            for i, s in enumerate(st):
                print(f"{'':<22}{'→' if i == p['current'] else ('✓' if i < p['current'] else ' ')} {i + 1}: {s}")


def cmd_show(a):
    day = a.day or israel_today()
    data = read_export()
    if not data:
        print("day.json ещё нет: Пульт не открывался после установки плана дня или в плане нет записей.")
    else:
        print(f"day.json записан {data.get('written')} (сегодня по Пульту {data.get('today')})")
        d = (data.get("days") or {}).get(day)
        if not d:
            print(f"{day}: плана нет")
        else:
            k = d.get("close") or {}
            print(f"{day}:" + (f"  закрыт, оценка {k['rating']}/10" if k.get("closed") else "") + (f"  итог дня: {d['note']}" if d.get("note") else ""))
            for it in d["items"]:
                where = f"[{it['project_name']}] " if it.get("project_name") else ""
                what = {"stage": "этап: ", "advance": "продвинуться: ", "task": ""}[it["kind"]]
                extra = f" → {it.get('moved_to_day')}" if it["status"] == "moved" else ""
                print(f"  {MARK[it['status']]}{PRIO[it['priority']]} {it['id']}  {where}{what}{it['title']}{extra}"
                      + (f"  — {it['note']}" if it.get("note") else "") + ("  (Claude)" if it["added_by"] == "claude" else ""))
    waiting = sorted(p.name for p in INBOX.glob("*.json")) if INBOX.is_dir() else []
    if waiting:
        print(f"Ждут Пульт ({len(waiting)}): " + ", ".join(waiting))


def cmd_result(a):
    if not APPLIED.is_dir():
        sys.exit("Итогов пока нет.")
    files = sorted(APPLIED.glob("*.result.json"))
    if a.name:
        files = [f for f in files if f.name.startswith(a.name)]
        if not files and (INBOX / a.name).is_file():
            sys.exit(f"{a.name} ещё ждёт Пульт (окно закрыто или не успело).")
    for f in files[-(a.last or 5):] if not a.name else files:
        r = json.loads(f.read_text(encoding="utf-8"))
        print(f"{r.get('name')}: {'принят' if r.get('ok') else 'НЕ принят — ' + str(r.get('error'))}" + (" (повтор)" if r.get("repeat") else ""))


def main():
    ap = argparse.ArgumentParser(description="План дня Пульта — запросы для Пульта (база не открывается)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("projects"); s.add_argument("--all", action="store_true"); s.set_defaults(fn=cmd_projects)
    s = sub.add_parser("show"); s.add_argument("--day"); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("add")
    s.add_argument("--day"); s.add_argument("--project"); s.add_argument("--stage", nargs="?", const="current")
    s.add_argument("--amount"); s.add_argument("--task"); s.add_argument("--title")
    s.add_argument("--priority", default="normal", choices=day_store.PRIORITIES); s.add_argument("--note")
    s.set_defaults(fn=lambda a: send([add_op(a)]))
    s = sub.add_parser("plan"); s.add_argument("--day"); s.add_argument("--file", required=True); s.add_argument("--replace", action="store_true")
    s.add_argument("--comment", default="")

    def plan(a):
        items = json.loads(pathlib.Path(a.file).read_text(encoding="utf-8-sig"))
        for it in items:
            it.setdefault("id", uuid.uuid4().hex)
            if isinstance(it.get("stage"), int) and not isinstance(it.get("stage"), bool):
                it["stage"] -= 1                        # на Пульте этапы с 1, в базе — с 0
        send([{"op": "plan", "day": a.day or israel_today(), "items": items, "replace": a.replace}], a.comment)
    s.set_defaults(fn=plan)
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("status", choices=day_store.SETTABLE); s.add_argument("--note")
    s.set_defaults(fn=lambda a: send([dict({"op": "status", "id": a.id, "status": a.status}, **({"note": a.note} if a.note is not None else {}))]))
    s = sub.add_parser("note"); s.add_argument("id"); s.add_argument("text")
    s.set_defaults(fn=lambda a: send([{"op": "note", "id": a.id, "note": a.text}]))
    s = sub.add_parser("priority"); s.add_argument("id"); s.add_argument("priority", choices=day_store.PRIORITIES)
    s.set_defaults(fn=lambda a: send([{"op": "priority", "id": a.id, "priority": a.priority}]))
    s = sub.add_parser("carry"); s.add_argument("id"); s.add_argument("--to")
    s.set_defaults(fn=lambda a: send([dict({"op": "carry", "id": a.id}, **({"to": a.to} if a.to else {}))]))
    s = sub.add_parser("restore"); s.add_argument("id"); s.set_defaults(fn=lambda a: send([{"op": "restore", "id": a.id}]))
    s = sub.add_parser("edit"); s.add_argument("id"); s.add_argument("--stage", type=int); s.add_argument("--amount"); s.add_argument("--title")

    def edit(a):
        op = {"op": "edit", "id": a.id}
        if a.stage is not None:
            op["stage"] = a.stage - 1                   # на Пульте этапы с 1, в базе — с 0
        if a.amount is not None:
            op["amount"] = a.amount
        if a.title is not None:
            op["title"] = a.title
        send([op])
    s.set_defaults(fn=edit)
    s = sub.add_parser("order"); s.add_argument("--day"); s.add_argument("ids", nargs="+")
    s.set_defaults(fn=lambda a: send([{"op": "order", "day": a.day or israel_today(), "ids": a.ids}]))
    s = sub.add_parser("day-note"); s.add_argument("--day"); s.add_argument("text")
    s.set_defaults(fn=lambda a: send([{"op": "day_note", "day": a.day or israel_today(), "note": a.text}]))
    s = sub.add_parser("close"); s.add_argument("--day"); s.add_argument("--rating", type=int, required=True); s.add_argument("--note")
    s.set_defaults(fn=lambda a: send([dict({"op": "close_day", "day": a.day or israel_today(), "rating": a.rating},
                                            **({"note": a.note} if a.note is not None else {}))]))
    s = sub.add_parser("reopen"); s.add_argument("--day"); s.set_defaults(fn=lambda a: send([{"op": "reopen_day", "day": a.day or israel_today()}]))
    s = sub.add_parser("carry-open"); s.add_argument("--day"); s.set_defaults(fn=lambda a: send([{"op": "carry_open", "day": a.day or israel_today()}]))
    s = sub.add_parser("result"); s.add_argument("name", nargs="?"); s.add_argument("--last", type=int); s.set_defaults(fn=cmd_result)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
