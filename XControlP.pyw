# -*- coding: utf-8 -*-
"""XControlP: открывает пульт проектов в отдельном окне.

1. Читает projects.json (главный файл с данными) и собирает из него data.js,
   который читает окно «XControlP.html».
2. Идеи. Главный источник — общая база идей (ideas_db в projects.json: путь к ideas.db).
   Её ведут исполнители скриптом ideas.py, каждый — в своих таблицах своим ключом; Пульт открывает
   базу только для чтения (общие виды ideas, notes, status_log, links). Каждый отдел
   базы с идеями — свой подотдел раздела «Идеи», история статусов берётся из журнала базы,
   у идеи видны её проект и связи.
   Если база не указана, пуста или не читается — как раньше, файлы идей (ideas_files — список
   подотделов; старое поле ideas_file тоже понимается), только чтение, и своя история
   ideas-history.json (новая запись — только когда итог идеи изменился).
3. Если рядом есть auto.json (итог последней синхронизации), добавляет его: этапы проектов
   с источником, последнюю активность и новые события. projects.json при этом не меняется.
4. Запускает маленький сервер только внутри компьютера (127.0.0.1) и открывает через него
   «XControlP.html» в Microsoft Edge как отдельное окно (без адресной строки).
   Сервер нужен для кнопки «Синхронизировать данные»: она просит его запустить сборщик
   (collect.py). Запросы принимаются только от самого окна Пульта: по ключу, который выдаётся
   при запуске. Сервер закрывается сам, когда окно Пульта закрыто (10 минут без запросов).
   Если сервер не запустился, окно открывается как файл, как раньше, — без кнопки.
   При каждом запуске программы окно само один раз запускает ту же синхронизацию; кнопка остаётся для повторной.
   Вторая синхронизация, пока идёт первая, не начинается: окно отвечает «Синхронизация уже идёт».
   Первый запуск: если projects.json нет, а есть templates/projects.example.json, шаблон копируется
   в projects.json (готовый projects.json никогда не перезаписывается).

Ярлык «XControlP» на рабочем столе (его делает create_shortcut.pyw) запускает этот файл; значок — icon.ico.

5. Календарь: если рядом есть google-client.json, Пульт по кнопке «Войти в Google»
   получает разрешение только на чтение Google Календаря (calendar_google.py), скачивает события в
   calendar.json и показывает их в разделе «Календарь» вместе с рабочими событиями самого Пульта.
   Календарь обновляется при запуске, каждые 30 минут, пока окно открыто, и кнопкой синхронизации.
   google-client.json, google-token*.json и calendar.json — только на этом компьютере, в git не идут.
   Аккаунтов Google может быть несколько: «+ Аккаунт» в разделе «Календарь» (разрешения google-token-2.json, -3 …).

6. План дня: вкладка «План дня» — задачи на день из проектов и этапов
   («завершить этап», «продвинуться: 1 урок», своя задача), очередь и приоритет, отметки выполнения,
   «на завтра». Хранится в day.db (SQLite, day_store.py); открывает её только эта программа.
   Claude пишет не в базу, а запросы в папку day-inbox (скрипт day.py) — программа применяет их сама,
   пока окно открыто (каждые 10 секунд), и пишет копию для чтения day.json. Этапы проектов план дня не двигает.
   Вкладка «Итоги дней» (08.10.2026): день закрывается с оценкой от 1 до 10 и итогом словами; итоги недель и месяцев.
   Раздел «Статистика» (17.10.2026): неделя и месяц (потом квартал и год) — план дня, движение проектов, уроки,
   идеи и коммиты, со сравнением с прошлым периодом. Уроки и коммиты по дням собирает сборщик (кнопка синхронизации).

7. Языки (этап Пульта «Меню языков», 08.10.2026): русский, английский, иврит (окно зеркальное).
   Выбор языка — settings.json (кнопки в меню слева, сохраняет эта программа). Надписи окна — i18n.js,
   данные (названия проектов, групп, этапов, описания, события) — translations.json; нет перевода — по-русски.

8. Сводки: раздел «Сводки» — ежедневные сводки новостей из git-репозитория сводок (digest_store.py).
   Репозиторий задаёт переменная окружения PULT_DIGEST_REPO или ключ digest_repo в projects.json; не задан —
   раздел пуст и ни одна команда git не запускается. Отметки «интересно» и «полезно» Пульт
   пишет в репозиторий и сразу делает коммит и push; кнопка синхронизации забирает новые сводки.

9. Исследования: папка research рядом с Пультом — реестр research.json
   и тексты .md (каждая запись на трёх языках и исходные документы). Пульт только читает их и кладёт
   в data.js; раздел «Исследования» и подраздел «Исследование рынка» в карточке услуги. Записи добавляет штаб.

10. Отчёты: недельные отчёты штаба из папки reports/weekly рядом с Пультом (другое место — reports_dir
   в projects.json). Даты недели берутся
   из имени файла «Weekly report ДД–ДД.ММ.ГГГГ.md» (старое «Недельный отчёт …» тоже понимается); месячные отчёты
   — из reports/monthly (при своём reports_dir — из папки Monthly рядом с ней), «Monthly report ГГГГ-ММ.md»
   (другое место — monthly_reports_dir); если папка лежит в git-репозитории с GitHub, ссылка ведёт на GitHub; отчёт, которого нет
   в origin/main, помечается «не отправлен». Пульт только читает: git ls-tree, без записи.

Окно само перечитывает data.js каждые 20 секунд. Пока окно открыто, программа пересобирает
data.js, как только изменились projects.json, база или файлы идей, — перезапускать ничего не нужно.
Нужен только Python 3, без установки пакетов.

Только собрать data.js, не открывая окно:  python XControlP.pyw --build
Взять первый файл идей из другого места:   python XControlP.pyw --build --ideas=ПУТЬ
"""
import datetime
import http.server
import importlib.util
import json
import os
import pathlib
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "projects.json"
TEMPLATE = HERE / "templates" / "projects.example.json"   # пустой projects.json для первого запуска
IDEAS_TEMPLATE = HERE / "templates" / "IDEAS.example.md"  # пустой файл идей для первого запуска
IDEAS_DEFAULT = HERE / "ideas" / "IDEAS.md"               # файл идей, который создаёт первый запуск
TARGET = HERE / "data.js"
AUTO = HERE / "auto.json"
HISTORY = HERE / "ideas-history.json"
PAGE = HERE / "XControlP.html"
COLLECTOR = HERE / "collect.py"
SYNC_LOG = HERE / "sync-last-error.txt"
CALENDAR_MODULE = HERE / "calendar_google.py"
CALENDAR_FILES = [HERE / "calendar.json", HERE / "google-client.json", HERE / "google-token.json"]
CALENDAR_EVERY = 30 * 60        # как часто обновлять календарь, пока окно открыто
TRANSLATIONS = HERE / "translations.json"
SETTINGS = HERE / "settings.json"
ALERTS = HERE / "alerts.json"           # отметки тревог: «в починке» и «убрана» (кнопки в окне)
ALERT_STATES = ("repair", "dismissed")
ALERT_KEEP_DAYS = 365                   # отметки старше года — забываются
RESEARCH_DIR = HERE / "research"       # отдел исследований: research.json (реестр) и тексты .md; Пульт только читает
RESEARCH = RESEARCH_DIR / "research.json"
RESEARCH_FILE = re.compile(r"^[^/\\:]+\.md$")
RESEARCH_MAX = 2_000_000   # байт на один текст
REPORT_NAME = re.compile(r"^(?:Weekly report|Недельный отчёт) (\d{1,2})(?:\.(\d{1,2}))?[–-](\d{1,2})\.(\d{1,2})\.(\d{4})\.md$")
MONTH_NAME = re.compile(r"^Monthly report (\d{4})-(\d{2})\.md$")
GIT_NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # git без мигающих окон консоли
REPORT_MAX = 2_000_000   # байт на текст отчёта и на его файл данных
FLAGS = HERE / "flags.json"             # реестр услуг: услуга закреплена, флажок снимается и ставится (кнопки в карточке идеи); база идей не меняется
IDEA_ID = re.compile(r"^[A-Z]{1,3}-\d{1,5}$")
LANGS = ("ru", "en", "he")
DAY_MODULE = HERE / "day_store.py"
REQUESTS_DIR = HERE / "requests"         # запросы штабу: кнопки «Запросить сводку дня» и «Запросить предложения»
ANSWERS_DIR = HERE / "answers"           # ответы штаба (pult-answer, три языка); пишет штаб
PROPOSALS = HERE / "proposals.json"     # отметки предложений: принято (в плане дня) или отклонено
REQUEST_KINDS = ("summary", "proposals")
REQUEST_BODY_LIMIT = 512 * 1024
PROPOSAL_STATES = ("accepted", "declined")
ANSWER_MAX = 2_000_000
PROPOSAL_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}\|[a-z0-9][a-z0-9-]{0,39}$")
DAY_COPY = HERE / "day.json"            # копия плана дня для чтения (пишет хранилище плана дня)
CARRY_OPEN = ("planned", "active", "partial", "not_done")
DIGEST_MODULE = HERE / "digest_store.py"
DAY_EVERY = 10                  # как часто смотреть запросы Claude в day-inbox, пока окно открыто
DAY_BODY_LIMIT = 64 * 1024
IDLE_SECONDS = 600

# pythonw запускается без консоли: всё, что пишется в консоль, уходит в никуда.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

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


_GCAL = []


def gcal():
    """Модуль календаря (calendar_google.py рядом с Пультом); загружается один раз. Нет файла — None."""
    if not _GCAL:
        module = None
        if CALENDAR_MODULE.is_file():
            try:
                spec = importlib.util.spec_from_file_location("pult_gcal", CALENDAR_MODULE)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception:
                module = None
        _GCAL.append(module)
    return _GCAL[0]


def calendar_data():
    """Для окна: скачанные события (calendar.json) и что настроено — без секретов."""
    module = gcal()
    if module is None:
        return {"available": False}
    cache = module.read_json(module.CACHE) or {}
    return dict(cache, available=True, setup=module.setup())


def calendar_connected(module):
    """Есть ли хоть одно разрешение Google (старый модуль знает только google-token.json)."""
    return module.connected() if hasattr(module, "connected") else module.TOKEN.is_file()


def calendar_sync_quiet():
    """Обновить календарь, если Пульт уже подключён к Google. Ошибка календаря не мешает остальному."""
    module = gcal()
    if module is None or not calendar_connected(module):
        return None
    try:
        return module.sync()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def read_translations():
    """translations.json: {"en": {русский текст: перевод}, "he": {...}}. Нет файла или сломан — без переводов."""
    try:
        raw = json.loads(TRANSLATIONS.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in raw.items() if k in LANGS and isinstance(v, dict)}


# Настройки окна: язык, стиль значков, общий стиль. Чужие значения не принимаются.
# Стили значков — подпапки icons со своим style.json; «base» — прежние символы, картинок не нужно.
SETTING_DEFAULTS = {"lang": "ru", "icons": "comic", "theme": "dark", "scale": "100", "accent": "orange"}


def setting_choices():
    return {"lang": LANGS, "icons": ("base",) + tuple(icon_styles()), "theme": ("dark", "light"),
            "scale": ("90", "100", "110", "125"), "accent": ("orange", "blue", "violet", "teal")}


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
    return result


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
    settings = dict(read_settings(), **changes)
    temporary = SETTINGS.with_name(f"settings.json.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, SETTINGS)
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()
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


def read_services():
    """flags.json — реестр услуг: {"services": {номер идеи: {"added": "ГГГГ-ММ-ДД", "flag": true|false, "flag_at": "ГГГГ-ММ-ДД"}}}.
    Услуга закреплена за отделом услуг: снятый флажок её не убирает. Старый вид {"flags": {номер: {"at": …}}} читается
    как услуги с флажком и переписывается в новый при первой записи. Нет файла — услуг нет."""
    try:
        raw = json.loads(FLAGS.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    old = raw.get("flags")
    if isinstance(old, dict):
        for k, v in old.items():
            if isinstance(k, str) and IDEA_ID.match(k) and isinstance(v, dict):
                at = str(v.get("at", ""))
                out[k] = {"added": at, "flag": True, "flag_at": at}
    new = raw.get("services")
    if isinstance(new, dict):
        for k, v in new.items():
            if isinstance(k, str) and IDEA_ID.match(k) and isinstance(v, dict):
                out[k] = {"added": str(v.get("added", "")), "flag": bool(v.get("flag")), "flag_at": str(v.get("flag_at", ""))}
    return out


def write_services(services):
    temporary = FLAGS.with_name(f"flags.json.{os.getpid()}.tmp")
    temporary.write_text(json.dumps({"services": dict(sorted(services.items()))}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, FLAGS)
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()


def known_idea_ids():
    """Номера всех идей, которые видит Пульт: из базы идей, а если её нет — из файлов идей."""
    data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    found = read_ideas_db(data)
    sets = found["sets"] if found and found.get("sets") else read_idea_sets(data)
    return {str(it.get("id")) for s in (sets or []) for it in (s.get("items") or [])}


def query_id(query):
    return ((query or {}).get("id") or [""])[0]


def save_flag(query):
    """Кнопка в карточке идеи: POST /idea/flag?id=A-37&on=1|0 → flags.json → data.js. База идей не меняется.
    on=1: идея становится услугой (если ещё не услуга) и получает зелёный флажок; on=0: флажок снят, услуга остаётся."""
    idea = query_id(query)
    on = ((query or {}).get("on") or [""])[0]
    if not IDEA_ID.match(idea):
        return {"ok": False, "error": f"неверный номер идеи: {idea!r}"}
    if on not in ("1", "0"):
        return {"ok": False, "error": f"неизвестное значение: {on!r}"}
    services = read_services()
    today = datetime.date.today().isoformat()
    if on == "1":
        if idea not in services:
            try:
                known = known_idea_ids()
            except (OSError, ValueError) as exc:
                return {"ok": False, "error": f"идеи не читаются: {exc}"}
            if idea not in known:
                return {"ok": False, "error": f"нет такой идеи: {idea}"}
            services[idea] = {"added": today, "flag": True, "flag_at": today}
        elif not services[idea]["flag"]:
            services[idea].update(flag=True, flag_at=today)
    elif idea in services and services[idea]["flag"]:
        services[idea].update(flag=False, flag_at=today)
    write_services(services)
    return {"ok": True, "id": idea, "on": on == "1", "service": idea in services}


def remove_service(query):
    """Кнопка «Убрать из услуг» (после подтверждения в окне): POST /idea/service-remove?id=… — услуга уходит
    из отдела услуг; сама идея в базе остаётся."""
    idea = query_id(query)
    if not IDEA_ID.match(idea):
        return {"ok": False, "error": f"неверный номер идеи: {idea!r}"}
    services = read_services()
    if idea not in services:
        return {"ok": True, "id": idea, "removed": False}
    services.pop(idea)
    write_services(services)
    return {"ok": True, "id": idea, "removed": True}


def read_research_text(name):
    """Текст из папки research: только простое имя файла .md, без путей; файла нет или он слишком большой — пусто."""
    if not isinstance(name, str) or name.startswith(".") or not RESEARCH_FILE.match(name):
        return ""
    path = RESEARCH_DIR / name
    try:
        if path.resolve().parent != RESEARCH_DIR.resolve() or path.stat().st_size > RESEARCH_MAX:
            return ""
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def read_research():
    """Отдел исследований: research.json → записи (новые сверху) с текстами по языкам и исходными документами."""
    if not RESEARCH.exists():
        return {"entries": [], "error": ""}
    try:
        raw = json.loads(RESEARCH.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return {"entries": [], "error": f"research.json не читается: {exc}"}
    entries = []
    for item in raw.get("research", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        files = item.get("text") if isinstance(item.get("text"), dict) else {}
        texts = {lang: read_research_text(name) for lang, name in files.items()}
        sources = [{"lang": src.get("lang", ""), "file": src.get("file", ""), "name": src.get("name") if isinstance(src.get("name"), dict) else {},
                    "text": read_research_text(src.get("file"))} for src in item.get("sources") or [] if isinstance(src, dict)]
        entries.append({"id": str(item["id"]), "date": str(item.get("date", "")), "kind": item.get("kind", ""),
                        "services": [str(x) for x in item.get("services") or []], "version": str(item.get("version", "")),
                        "original": item.get("original", ""), "title": item.get("title") if isinstance(item.get("title"), dict) else {},
                        "answer": item.get("answer") if isinstance(item.get("answer"), dict) else {},
                        "text": {k: v for k, v in texts.items() if v}, "missing": [files[k] for k, v in texts.items() if not v],
                        "sources": sources})
    entries.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    return {"entries": entries, "error": ""}


def reports_dir(data):
    """Папка недельных отчётов: reports_dir из projects.json, иначе reports/weekly рядом с Пультом."""
    if data.get("reports_dir"):
        return pathlib.Path(os.path.expanduser(str(data["reports_dir"])))
    return HERE / "reports" / "weekly"


def monthly_dir(data):
    """Папка месячных отчётов: monthly_reports_dir из projects.json; иначе при своём reports_dir — папка Monthly
    рядом с ней, без него — reports/monthly рядом с Пультом."""
    if data.get("monthly_reports_dir"):
        return pathlib.Path(os.path.expanduser(str(data["monthly_reports_dir"])))
    if data.get("reports_dir"):
        return reports_dir(data).parent / "Monthly"
    return HERE / "reports" / "monthly"


def month_dates(name):
    """«Monthly report 2026-10.md» → ("2026-10-01", "2026-10-31")."""
    m = MONTH_NAME.match(name)
    if not m:
        return None
    year, month = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        return None
    end = datetime.date(year + (month == 12), month % 12 + 1, 1) - datetime.timedelta(days=1)
    return datetime.date(year, month, 1).isoformat(), end.isoformat()


def git_root(path):
    for folder in [path] + list(path.parents):
        if (folder / ".git").exists():
            return folder
    return None


def github_base(root):
    """https://github.com/<владелец>/<репозиторий> из .git/config (remote origin); не GitHub — пусто."""
    try:
        text = (root / ".git" / "config").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    block = re.search(r'\[remote "origin"\]([^\[]*)', text)
    url = re.search(r"^\s*url\s*=\s*(\S+)", block.group(1), re.M) if block else None
    m = re.match(r"^(?:https://github\.com/|git@github\.com:)([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url.group(1)) if url else None
    return f"https://github.com/{m.group(1)}/{m.group(2)}" if m else ""


def report_dates(name):
    """«Weekly report 11–17.10.2026.md» → ("2026-10-11", "2026-10-17"); неделя может перейти через месяц и год."""
    m = REPORT_NAME.match(name)
    if not m:
        return None
    d1, m1, d2, m2, year = m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5))
    try:
        end = datetime.date(year, int(m2), int(d2))
        month1 = int(m1) if m1 else end.month
        start = datetime.date(year - 1 if month1 > end.month else year, month1, int(d1))
    except ValueError:
        return None
    return (start.isoformat(), end.isoformat()) if start <= end and (end - start).days <= 13 else None


def git_names_on_origin(root, rel):
    """Имена файлов папки rel в origin/main (по последнему fetch). Git нет или ошибка — None."""
    import shutil
    exe = shutil.which("git")
    if not exe:
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
            for tail in (r"Git\cmd\git.exe", r"Programs\Git\cmd\git.exe"):
                if base and (pathlib.Path(base) / tail).is_file():
                    exe = str(pathlib.Path(base) / tail)
    if not exe:
        return None
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    try:
        done = subprocess.run([exe, "-C", str(root), "-c", "core.quotepath=off", "ls-tree", "-z", "--name-only", "origin/main", "--", rel + "/"],
                              capture_output=True, timeout=20, env=env, creationflags=GIT_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return {x.rsplit("/", 1)[-1] for x in done.stdout.decode("utf-8", "replace").split("\0") if x}


def read_report_files(path):
    """Оригинал отчёта (.md) и его файл данных (.json рядом, с тем же именем). Слишком большой или испорченный — пусто и причина."""
    text = ""
    try:
        if path.stat().st_size <= REPORT_MAX:
            text = path.read_text(encoding="utf-8-sig")
    except OSError:
        pass
    side = path.with_suffix(".json")
    if not side.exists():
        return text, None, ""
    try:
        if side.stat().st_size > REPORT_MAX:
            return text, None, "too_big"
        raw = json.loads(side.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return text, None, "bad_json"
    if not isinstance(raw, dict) or raw.get("format") != "pult-report" or raw.get("version") != 1 or not isinstance(raw.get("categories"), list):
        return text, None, "bad_format"
    return text, raw, ""


def read_report_folder(folder, dates_of):
    """Отчёты одной папки (новые сверху): оригинал, файл данных и пометка «не отправлен». Второе значение — ответил ли git."""
    root = git_root(folder)
    rel = folder.relative_to(root).as_posix() if root else ""
    on_origin = git_names_on_origin(root, rel) if root else None
    entries = []
    for path in folder.glob("*.md"):
        dates = dates_of(path.name)
        if not dates:
            continue
        text, report, problem = read_report_files(path)
        entries.append({"file": path.name, "start": dates[0], "end": dates[1], "text": text, "data": report, "data_error": problem,
                        "pushed": None if on_origin is None else path.name in on_origin})
    entries.sort(key=lambda e: e["end"], reverse=True)
    return entries, on_origin is not None


def read_reports(data):
    """Раздел «Отчёты»: недельные (entries) и месячные (months) отчёты, новые сверху."""
    folder = reports_dir(data)
    mfolder = monthly_dir(data)
    months, months_git = read_report_folder(mfolder, month_dates) if mfolder.is_dir() else ([], True)
    if not folder.is_dir():
        return {"entries": [], "months": months, "dir": str(folder), "months_dir": str(mfolder), "error": "no_dir"}
    entries, weeks_git = read_report_folder(folder, report_dates)
    git_ok = weeks_git and months_git
    return {"entries": entries, "months": months, "dir": str(folder), "months_dir": str(mfolder),
            "error": "" if git_ok or not (entries or months) else "no_git"}


def reveal_report(query):
    """«Показать в папке»: Проводник открывается на файле отчёта. Только недельные и месячные отчёты из их папок."""
    name = (query.get("file") or [""])[0]
    if not REPORT_NAME.match(name) and not MONTH_NAME.match(name):
        return {"ok": False, "error": "name"}
    try:
        data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {"ok": False, "error": "projects.json"}
    folder = reports_dir(data) if REPORT_NAME.match(name) else monthly_dir(data)
    path = folder / name
    if not path.is_file() or path.resolve().parent != folder.resolve():
        return {"ok": False, "error": "missing"}
    if os.name != "nt":
        return {"ok": False, "error": "windows"}
    subprocess.Popen(["explorer", "/select,", str(path)], close_fds=True)
    return {"ok": True}


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


def run_sync():
    """Кнопка «Синхронизировать данные»: сборщик → auto.json → data.js. Возвращает итог для окна."""
    with SYNC_LOCK:
        before = effective_stages()
        old_auto = read_auto() or {}
        spec = importlib.util.spec_from_file_location("pult_collect", COLLECTOR)
        collector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collector)
        auto = collector.collect(fetch=True)
        calendar = calendar_sync_quiet()
        digest = digest_sync()
        data = build() or {}
        projects = {p.get("id"): p for p in data.get("projects", [])}
        old_events = {(e.get("date"), pid, e.get("text"))
                      for pid, r in (old_auto.get("projects") or {}).items() for e in r.get("events", [])}
        new_events = sum(1 for pid, r in auto["projects"].items() for e in r.get("events", [])
                         if (e.get("date"), pid, e.get("text")) not in old_events)
        lines = []
        for pid, result in auto["projects"].items():
            p = projects.get(pid, {})
            stages = p.get("stages") or []
            now, was = p.get("current", 0), before.get(pid, 0)
            line = {"id": pid, "name": result.get("name", pid), "ok": result.get("ok", False), "error": result.get("error", "")}
            if result.get("ok"):
                line.update(stage=stages[now] if stages else "", moved=now != was, was=stages[was] if now != was and stages else "")
            lines.append(line)
        return {"ok": True, "synced": auto.get("synced"), "seconds": auto.get("seconds"), "projects": lines,
                "notes": auto.get("notes", []), "events": new_events, "calendar": calendar, "digest": digest}


SYNC_GATE = threading.Lock()          # одна синхронизация за раз: по кнопке или при запуске
STARTUP_SYNC = {"started": False}
STARTUP_LOCK = threading.Lock()


def sync_request():
    """Кнопка: если синхронизация уже идёт (при запуске или из другого окна), вторая не начинается."""
    if not SYNC_GATE.acquire(blocking=False):
        return {"ok": False, "busy": True, "error": "Синхронизация уже идёт"}
    try:
        return run_sync()
    finally:
        SYNC_GATE.release()


def startup_sync_request():
    """Синхронизация при включении Пульта: один раз за запуск программы; перезагрузка окна её не повторяет."""
    with STARTUP_LOCK:
        if STARTUP_SYNC["started"]:
            return {"ok": True, "skipped": True}
        STARTUP_SYNC["started"] = True
    return sync_request()


def calendar_login(query=None, add=False):
    """Кнопки «Войти в Google» / «Войти снова» / «+ Аккаунт»: окно Google открывается в браузере, вход идёт в фоне."""
    module = gcal()
    if module is None:
        return {"ok": False, "error": "Нет файла calendar_google.py рядом с Пультом."}
    if not module.CLIENT.is_file():
        return {"ok": False, "error": "Нет файла google-client.json в папке Пульта."}
    hint = ((query or {}).get("account") or [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", hint or "x@x"):
        hint = ""
    try:
        started = module.start_login(add=add, hint=hint)
    except TypeError:                     # старый calendar_google.py без нескольких аккаунтов
        started = module.start_login()
    return {"ok": True, "started": started}


def calendar_add(query=None):
    return calendar_login(query, add=True)


def calendar_sync_now():
    """Кнопка «Обновить» в разделе «Календарь»."""
    module = gcal()
    if module is None:
        return {"ok": False, "error": "Нет файла calendar_google.py рядом с Пультом."}
    with SYNC_LOCK:
        result = module.sync()
        build()
        LAST_STAMPS[0] = stamps()
    return result


def calendar_keeper():
    """Пока Пульт открыт: календарь обновляется при запуске (если устарел) и каждые 30 минут."""
    module = gcal()
    if module is None:
        return
    first = True
    while True:
        if calendar_connected(module):
            age = module.cache_age_minutes()
            if not first or age is None or age > 30:
                with SYNC_LOCK:
                    try:
                        module.sync()
                    except Exception:
                        pass
        first = False
        time.sleep(CALENDAR_EVERY)


# ---------------------------------------------------------------- сводки

_DIGEST = []
DIGEST_PROBLEM = ["Нет файла digest_store.py рядом с Пультом."]


def digest_repo():
    """Репозиторий сводок: переменная окружения PULT_DIGEST_REPO или ключ digest_repo в projects.json.
    Не задан — None: раздел «Сводки» пуст, ни одна команда git не запускается. Репозитория по умолчанию нет."""
    value = os.environ.get("PULT_DIGEST_REPO") or ""
    if not value.strip():
        try:
            data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            data = {}
        value = str(data.get("digest_repo") or "") if isinstance(data, dict) else ""
    return os.path.expanduser(value.strip()) if value.strip() else None


def digest_store():
    """Сводки (digest_store.py рядом с Пультом): модуль загружается один раз, хранилище создаётся заново,
    когда сменился репозиторий сводок. Не загрузилось — None (причина в DIGEST_PROBLEM)."""
    if not _DIGEST:
        module = None
        if DIGEST_MODULE.is_file():
            try:
                spec = importlib.util.spec_from_file_location("pult_digest", DIGEST_MODULE)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as exc:
                DIGEST_PROBLEM[0] = f"digest_store.py не загрузился: {type(exc).__name__}: {exc}"
                module = None
        _DIGEST.append({"module": module, "repo": None, "store": None})
    entry = _DIGEST[0]
    if entry["module"] is None:
        return None
    repo = digest_repo()
    if entry["store"] is None or entry["repo"] != repo:
        try:
            entry["store"] = entry["module"].Digests(repo)
        except Exception as exc:
            DIGEST_PROBLEM[0] = f"digest_store.py не загрузился: {type(exc).__name__}: {exc}"
            entry["store"] = None
            return None
        entry["repo"] = repo
    return entry["store"]


def digest_view():
    """Сводки и отметки для окна (data.js). Ошибка — текстом в окно, Пульт работает дальше."""
    store = digest_store()
    if store is None:
        return {"ok": False, "error": DIGEST_PROBLEM[0], "digests": []}
    try:
        return store.view()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "digests": []}


def digest_stamp():
    store = digest_store()
    try:
        return store.stamp() if store is not None else None
    except Exception:
        return None


def digest_sync():
    """Кнопка «Синхронизировать данные»: новые сводки с GitHub и отправка отметок."""
    store = digest_store()
    if store is None:
        return {"ok": False, "error": DIGEST_PROBLEM[0]}
    if store.repo is None:
        return None          # репозиторий сводок не задан: синхронизировать нечего, git не запускается
    try:
        return store.sync()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def digest_mark(query):
    """Кнопки «Интересно» и «Полезно»: POST /digest/mark?date=…&id=…&kind=interesting|useful&value=1|0."""
    q = lambda key: ((query or {}).get(key) or [""])[0]
    store = digest_store()
    if store is None:
        return {"ok": False, "error": DIGEST_PROBLEM[0]}
    try:
        result = store.mark(q("date"), q("id"), q("kind"), q("value") == "1")
    except Exception as exc:
        return {"ok": False, "error": str(exc) if exc.__class__.__name__ == "DigestError" else f"{type(exc).__name__}: {exc}"}
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()
    return result


# ---------------------------------------------------------------- план дня

_DAY = []
DAY_PROBLEM = ["Нет файла day_store.py рядом с Пультом."]


def day_store():
    """Хранилище плана дня (day_store.py рядом с Пультом); загружается один раз. Не загрузилось — None (причина в DAY_PROBLEM)."""
    if not _DAY:
        store = None
        if DAY_MODULE.is_file():
            try:
                spec = importlib.util.spec_from_file_location("pult_day", DAY_MODULE)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                store = module.Store(HERE)
            except Exception as exc:
                DAY_PROBLEM[0] = f"day_store.py не загрузился: {type(exc).__name__}: {exc}"
                store = None
        _DAY.append(store)
    return _DAY[0]


def day_error(exc):
    return {"ok": False, "error": str(exc) if exc.__class__.__name__ == "DayError" else f"{type(exc).__name__}: {exc}"}


def day_view(query):
    """GET /day.json?day=2026-10-07 — задачи дня; сначала применить ждущие запросы Claude."""
    store = day_store()
    if store is None:
        return {"ok": False, "error": DAY_PROBLEM[0]}, 200
    day = ((query or {}).get("day") or [datetime.date.today().isoformat()])[0]
    try:
        applied = store.process_inbox()
        result = store.view(day)
        result["applied"] = applied
        return result, 200
    except Exception as exc:
        return day_error(exc), 200


def day_review(query):
    """GET /day-review.json?from=…&to=… — итоги дней для вкладки «Итоги дней»."""
    store = day_store()
    if store is None:
        return {"ok": False, "error": DAY_PROBLEM[0]}, 200
    today = datetime.date.today()
    first = ((query or {}).get("from") or [(today - datetime.timedelta(days=370)).isoformat()])[0]
    last = ((query or {}).get("to") or [(today + datetime.timedelta(days=31)).isoformat()])[0]
    try:
        store.process_inbox()
        return store.review(first, last), 200
    except Exception as exc:
        return day_error(exc), 200


def day_op(body):
    """POST /day/op {"day": …, "ops": [...]} — изменения из окна; ответ — свежий вид дня."""
    store = day_store()
    if store is None:
        return {"ok": False, "error": DAY_PROBLEM[0]}, 200
    try:
        request = json.loads(body.decode("utf-8"))
        if not isinstance(request, dict):
            raise ValueError("нужен объект")
        results = store.apply(request.get("ops"), by="pult")
        result = store.view(request.get("day") or datetime.date.today().isoformat())
        result["results"] = results
        return result, 200
    except Exception as exc:
        return day_error(exc), 200


def day_keeper():
    """Пока Пульт открыт: запросы Claude из day-inbox применяются сами, каждые 10 секунд."""
    store = day_store()
    if store is None:
        return
    while True:
        try:
            if store.pending():
                store.process_inbox()
        except Exception:
            pass
        time.sleep(DAY_EVERY)


# ---------------------------------------------------------------- локальный сервер

class Pult(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.token = secrets.token_urlsafe(24)
        self.host = f"127.0.0.1:{self.server_address[1]}"
        self.seen = time.monotonic()


FILES = {"/data.js": ("data.js", "text/javascript; charset=utf-8"),
         "/i18n.js": ("i18n.js", "text/javascript; charset=utf-8"),
         "/icon.svg": ("icon.svg", "image/svg+xml"),
         "/icon.ico": ("icon.ico", "image/x-icon")}
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


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "Pult/1"

    def log_message(self, *args):
        pass

    def allowed(self):
        self.server.seen = time.monotonic()
        if self.headers.get("Host") != self.server.host:      # защита от чужих сайтов под видом 127.0.0.1
            self.send_error(403)
            return False
        return True

    def send(self, status, body, kind, cache="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.allowed():
            return
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            page = PAGE.read_text(encoding="utf-8")
            meta = f'<meta name="pult-token" content="{self.server.token}">'
            page = page.replace("</head>", meta + "\n</head>", 1)
            self.send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/day-review.json":
            result, status = day_review(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
            self.send(status, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif path == "/day.json":
            result, status = day_view(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
            self.send(status, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif path in FILES:
            if path == "/data.js":
                rebuild_if_changed()
            name, kind = FILES[path]
            try:
                self.send(200, (HERE / name).read_bytes(), kind)
            except OSError:
                self.send_error(404)
        elif ICON_PATH.match(path):
            # картинка запоминается окном, чтобы меню не мигало при обновлении
            sid, name = ICON_PATH.match(path).groups()
            style = icon_styles().get(sid)
            try:
                if not style:
                    raise OSError(sid)
                body = (style["folder"] / (name + ".png")).read_bytes()
            except OSError:
                self.send_error(404)
                return
            self.send(200, body, "image/png", cache="private, max-age=86400")
        else:
            self.send_error(404)

    def do_POST(self):
        if not self.allowed():
            return
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
        actions = {"/sync": sync_request, "/sync/startup": startup_sync_request, "/calendar/login": lambda: calendar_login(query),
                   "/calendar/add": lambda: calendar_add(query), "/calendar/sync": calendar_sync_now,
                   "/settings": lambda: save_settings(query), "/alerts": lambda: save_alert(query),
                   "/digest/mark": lambda: digest_mark(query), "/idea/flag": lambda: save_flag(query),
                   "/idea/service-remove": lambda: remove_service(query), "/report/reveal": lambda: reveal_report(query),
                   "/proposal": lambda: save_proposal(query)}
        if path not in actions and path not in ("/day/op", "/request"):
            self.send_error(404)
            return
        if self.headers.get("Origin") != "http://" + self.server.host or \
                not secrets.compare_digest(self.headers.get("X-Pult-Token", ""), self.server.token):
            self.send_error(403)
            return
        if path in ("/day/op", "/request"):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            limit = DAY_BODY_LIMIT if path == "/day/op" else REQUEST_BODY_LIMIT
            if not 0 < length <= limit or not (self.headers.get("Content-Type") or "").startswith("application/json"):
                self.send_error(400)
                return
            if path == "/request":
                try:
                    result, status = write_request(query, self.rfile.read(length)), 200
                except OSError as exc:
                    result, status = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500
            else:
                result, status = day_op(self.rfile.read(length))
            self.server.seen = time.monotonic()
            self.send(status, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        try:
            result, status = actions[path](), 200
        except Exception as exc:
            report = traceback.format_exc()
            try:
                SYNC_LOG.write_text(datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + "\n\n" + report, encoding="utf-8")
            except OSError:
                pass
            result, status = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500
        self.server.seen = time.monotonic()
        self.send(status, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")


def watchdog(server):
    """Окно закрыто — запросов нет — сервер закрывается сам."""
    while True:
        time.sleep(30)
        if time.monotonic() - server.seen > IDLE_SECONDS and not SYNC_LOCK.locked():
            server.shutdown()
            return


# ---------------------------------------------------------------- запуск

def edge():
    names = [
        (os.environ.get("ProgramFiles(x86)"), r"Microsoft\Edge\Application\msedge.exe"),
        (os.environ.get("ProgramFiles"), r"Microsoft\Edge\Application\msedge.exe"),
        (os.environ.get("LOCALAPPDATA"), r"Microsoft\Edge\Application\msedge.exe"),
    ]
    for base, tail in names:
        if base:
            path = pathlib.Path(base) / tail
            if path.is_file():
                return str(path)
    return None


def open_window(url):
    browser = edge()
    if browser:
        subprocess.Popen([browser, f"--app={url}", "--start-maximized"], close_fds=True)
    else:
        webbrowser.open(url)


def first_start():
    """Первый запуск: projects.json нет, а шаблон есть — копия шаблона становится projects.json.
    Существующий projects.json не перезаписывается никогда (файл открывается в режиме «x»)."""
    if SOURCE.exists() or not TEMPLATE.is_file():
        return
    try:
        with open(SOURCE, "xb") as out:
            out.write(TEMPLATE.read_bytes())
    except OSError:
        return               # уже есть или не записать — build() покажет причину в окне
    if IDEAS_TEMPLATE.is_file() and not IDEAS_DEFAULT.exists():
        try:
            IDEAS_DEFAULT.parent.mkdir(exist_ok=True)
            with open(IDEAS_DEFAULT, "xb") as out:
                out.write(IDEAS_TEMPLATE.read_bytes())
        except OSError:
            pass


def main():
    first_start()
    build()
    LAST_STAMPS[0] = stamps()
    if "--build" in sys.argv:
        return
    try:
        server = Pult()
    except OSError:
        open_window(PAGE.as_uri())          # как раньше: окно из файла, без кнопки синхронизации
        return
    threading.Thread(target=watchdog, args=(server,), daemon=True).start()
    threading.Thread(target=calendar_keeper, daemon=True).start()
    threading.Thread(target=day_keeper, daemon=True).start()
    open_window(f"http://{server.host}/")
    server.serve_forever()
    server.server_close()


if __name__ == "__main__":
    main()
