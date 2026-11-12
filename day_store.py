# -*- coding: utf-8 -*-
"""План дня: хранилище вкладки «План дня» Пульта.

Что где лежит (папка Пульта):
  day.db               база плана дня (SQLite). Открывает её ТОЛЬКО программа Пульта на этом компьютере:
                       один писатель. Claude в базу не пишет и её не открывает.
  day.json             копия для чтения (для Claude и любого читателя); пишется после каждого изменения.
  day-inbox/           запросы от Claude: файлы *.json, каждый создаётся один раз (сначала *.tmp, потом
                       переименование). Пульт применяет их сам, по порядку имён, и переносит в
                       day-inbox/applied/ вместе с итогом (*.result.json). Повтор того же файла не применяется дважды.
  day-plan-backups/    копии базы, сделанные самой SQLite: раз в день и перед сменой схемы. Не перезаписываются.

Правила (плагин database-building):
  * база сама отказывает неверным данным: CHECK, NOT NULL, внешние ключи, триггеры;
  * задачи не удаляются: «убрать» — это статус removed, его можно вернуть; журнал item_log только дописывается;
  * номер схемы в файле (PRAGMA user_version), шаги схемы только вперёд; файл более новой версии не открывается;
  * journal_mode=TRUNCATE + synchronous=FULL, foreign_keys и recursive_triggers включены, запись — BEGIN IMMEDIATE.
Этапы проектов план дня не двигает: этап на Пульте передвигает штаб.
Нужен только Python 3 со встроенным sqlite3.
"""
import datetime
import json
import os
import pathlib
import re
import sqlite3
import threading
import time
import uuid

SCHEMA_VERSION = 2                           # v2 (08.10.2026): итоги дней — оценка 1–10 и закрытие дня
FORMAT = 1                                   # формат файлов запросов и day.json
STATUSES = ("planned", "active", "done", "partial", "not_done", "moved", "removed")
SETTABLE = ("planned", "active", "done", "partial", "not_done", "removed")
OPEN = ("planned", "active", "partial", "not_done")          # такие можно перенести на завтра
PRIORITIES = ("high", "normal", "low")
KINDS = ("stage", "advance", "task")
BY = ("pult", "claude")
MAX_REQUEST = 256 * 1024                     # предел файла запроса
MAX_OPS = 200                                # предел действий в одном запросе
EXPORT_DAYS_BACK = 60                        # day.json: дни от (сегодня − 60) и все будущие
REQUEST_WAIT = 10                            # недописанный запрос моложе 10 с — подождать

ID_RE = re.compile(r"^[0-9a-f]{32}$")
REQUEST_RE = re.compile(r"^[0-9A-Za-z._-]{1,120}\.json$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SPACES = re.compile(r"\s+")

LABEL = {"planned": "запланировано", "active": "в работе", "done": "сделано", "partial": "частично",
         "not_done": "не сделано", "moved": "перенесено", "removed": "убрано"}


class DayError(ValueError):
    """Понятная ошибка: её текст видят CEO в окне и Claude в итоге запроса."""


MIGRATIONS = [
    # v1 — 07.10.2026
    """
CREATE TABLE day_notes (
  day TEXT PRIMARY KEY CHECK (date(day) IS NOT NULL AND date(day) = day),
  note TEXT NOT NULL CHECK (length(note) <= 4000),
  updated_at TEXT NOT NULL CHECK (length(updated_at) >= 19)
);
CREATE TABLE items (
  id TEXT PRIMARY KEY CHECK (length(id) = 32 AND id NOT GLOB '*[^0-9a-f]*'),
  day TEXT NOT NULL CHECK (date(day) IS NOT NULL AND date(day) = day),
  position INTEGER NOT NULL CHECK (typeof(position) = 'integer' AND position >= 0),
  priority TEXT NOT NULL CHECK (priority IN ('high', 'normal', 'low')),
  kind TEXT NOT NULL CHECK (kind IN ('stage', 'advance', 'task')),
  project_id TEXT CHECK (project_id IS NULL OR length(project_id) BETWEEN 1 AND 64),
  project_name TEXT CHECK (project_name IS NULL OR length(project_name) BETWEEN 1 AND 200),
  stage_index INTEGER CHECK (stage_index IS NULL OR (typeof(stage_index) = 'integer' AND stage_index >= 0)),
  stage_name TEXT CHECK (stage_name IS NULL OR length(stage_name) BETWEEN 1 AND 300),
  amount TEXT CHECK (amount IS NULL OR length(trim(amount)) BETWEEN 1 AND 200),
  title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 300),
  status TEXT NOT NULL CHECK (status IN ('planned', 'active', 'done', 'partial', 'not_done', 'moved', 'removed')),
  note TEXT NOT NULL CHECK (length(note) <= 2000),
  moved_to TEXT REFERENCES items(id),
  moved_from TEXT REFERENCES items(id),
  added_by TEXT NOT NULL CHECK (added_by IN ('pult', 'claude')),
  created_at TEXT NOT NULL CHECK (length(created_at) >= 19),
  updated_at TEXT NOT NULL CHECK (length(updated_at) >= 19),
  CHECK (kind <> 'stage' OR (project_id IS NOT NULL AND stage_index IS NOT NULL AND stage_name IS NOT NULL)),
  CHECK (kind = 'stage' OR (stage_index IS NULL AND stage_name IS NULL)),
  CHECK (kind <> 'advance' OR (project_id IS NOT NULL AND amount IS NOT NULL)),
  CHECK (kind = 'advance' OR amount IS NULL),
  CHECK ((project_id IS NULL) = (project_name IS NULL)),
  CHECK ((status = 'moved') = (moved_to IS NOT NULL)),
  CHECK (moved_to IS NULL OR moved_to <> id),
  CHECK (moved_from IS NULL OR moved_from <> id)
);
CREATE INDEX items_by_day ON items(day, position);
CREATE UNIQUE INDEX items_carried_once ON items(moved_from) WHERE moved_from IS NOT NULL;
CREATE TABLE item_log (
  n INTEGER PRIMARY KEY,
  item_id TEXT NOT NULL REFERENCES items(id),
  at TEXT NOT NULL CHECK (length(at) >= 19),
  by TEXT NOT NULL CHECK (by IN ('pult', 'claude')),
  action TEXT NOT NULL CHECK (action IN ('add', 'status', 'note', 'priority', 'order', 'carry', 'edit')),
  old TEXT,
  new TEXT
);
CREATE INDEX item_log_by_item ON item_log(item_id, n);
CREATE TABLE requests (
  name TEXT PRIMARY KEY CHECK (length(name) BETWEEN 6 AND 125),
  at TEXT NOT NULL CHECK (length(at) >= 19),
  ok INTEGER NOT NULL CHECK (ok IN (0, 1)),
  result TEXT NOT NULL
);
CREATE TRIGGER items_no_delete BEFORE DELETE ON items
BEGIN SELECT RAISE(ABORT, 'план дня: задачи не удаляются — поставьте статус «убрано»'); END;
CREATE TRIGGER items_fixed BEFORE UPDATE ON items
WHEN NEW.id IS NOT OLD.id OR NEW.day IS NOT OLD.day OR NEW.kind IS NOT OLD.kind OR NEW.project_id IS NOT OLD.project_id
  OR NEW.moved_from IS NOT OLD.moved_from OR NEW.added_by IS NOT OLD.added_by OR NEW.created_at IS NOT OLD.created_at
BEGIN SELECT RAISE(ABORT, 'план дня: день, проект и вид задачи не меняются — уберите задачу и добавьте новую'); END;
CREATE TRIGGER items_moved_final BEFORE UPDATE ON items
WHEN OLD.status = 'moved' AND (NEW.status IS NOT 'moved' OR NEW.moved_to IS NOT OLD.moved_to)
BEGIN SELECT RAISE(ABORT, 'план дня: перенесённая задача уже живёт в другом дне'); END;
CREATE TRIGGER item_log_no_update BEFORE UPDATE ON item_log
BEGIN SELECT RAISE(ABORT, 'журнал плана дня только дописывается'); END;
CREATE TRIGGER item_log_no_delete BEFORE DELETE ON item_log
BEGIN SELECT RAISE(ABORT, 'журнал плана дня только дописывается'); END;
CREATE TRIGGER requests_no_update BEFORE UPDATE ON requests
BEGIN SELECT RAISE(ABORT, 'журнал запросов только дописывается'); END;
CREATE TRIGGER requests_no_delete BEFORE DELETE ON requests
BEGIN SELECT RAISE(ABORT, 'журнал запросов только дописывается'); END;
CREATE TRIGGER day_notes_no_delete BEFORE DELETE ON day_notes
BEGIN SELECT RAISE(ABORT, 'заметки дня не удаляются'); END;
""",
    # v2 — 08.10.2026: итоги дней (вкладка «Итоги дней»): оценка дня от 1 до 10, день закрыт или открыт снова
    """
CREATE TABLE day_close (
  day TEXT PRIMARY KEY CHECK (date(day) IS NOT NULL AND date(day) = day),
  rating INTEGER NOT NULL CHECK (typeof(rating) = 'integer' AND rating BETWEEN 1 AND 10),
  closed INTEGER NOT NULL CHECK (closed IN (0, 1)),
  closed_at TEXT NOT NULL CHECK (length(closed_at) >= 19),
  updated_at TEXT NOT NULL CHECK (length(updated_at) >= 19)
);
CREATE TABLE day_log (
  n INTEGER PRIMARY KEY,
  day TEXT NOT NULL CHECK (date(day) IS NOT NULL AND date(day) = day),
  at TEXT NOT NULL CHECK (length(at) >= 19),
  by TEXT NOT NULL CHECK (by IN ('pult', 'claude')),
  action TEXT NOT NULL CHECK (action IN ('close', 'rate', 'reopen')),
  old TEXT,
  new TEXT
);
CREATE TRIGGER day_close_no_delete BEFORE DELETE ON day_close
BEGIN SELECT RAISE(ABORT, 'итоги дня не удаляются — день можно открыть снова'); END;
CREATE TRIGGER day_log_no_update BEFORE UPDATE ON day_log
BEGIN SELECT RAISE(ABORT, 'журнал итогов дня только дописывается'); END;
CREATE TRIGGER day_log_no_delete BEFORE DELETE ON day_log
BEGIN SELECT RAISE(ABORT, 'журнал итогов дня только дописывается'); END;
""",
]


# ---------------------------------------------------------------- мелочи

def now_text():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def today_key():
    return datetime.date.today().isoformat()


def check_day(value, what="день"):
    if not isinstance(value, str) or not DAY_RE.match(value):
        raise DayError(f"{what}: нужна дата вида 2026-10-07, а пришло {value!r}")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise DayError(f"{what}: такой даты нет — {value}")
    return value


def one_line(value, what, limit, required=True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise DayError(f"не задано: {what}")
        return None
    if not isinstance(value, str):
        raise DayError(f"{what}: нужен текст")
    text = SPACES.sub(" ", value).strip()
    if len(text) > limit:
        raise DayError(f"{what}: не длиннее {limit} знаков (сейчас {len(text)})")
    return text


def note_text(value, limit=2000):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise DayError("заметка: нужен текст")
    text = value.replace("\r\n", "\n").strip()
    if len(text) > limit:
        raise DayError(f"заметка: не длиннее {limit} знаков (сейчас {len(text)})")
    return text


def write_atomic(path, text):
    """Записать файл целиком через временный и переименование. Занят читателем — несколько попыток."""
    path = pathlib.Path(path)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    for attempt in range(5):
        try:
            os.replace(temporary, path)
            return True
        except PermissionError:
            time.sleep(0.2 * (attempt + 1))
    return False


def load_projects(folder):
    """Проекты и их этапы как их показывает Пульт: projects.json, этап — с учётом auto.json (назад не уходит)."""
    folder = pathlib.Path(folder)
    try:
        data = json.loads((folder / "projects.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise DayError(f"projects.json не читается: {exc}")
    try:
        auto = json.loads((folder / "auto.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        auto = {}
    result = {}
    for p in data.get("projects", []):
        pid = p.get("id")
        if not isinstance(pid, str) or not pid:
            continue
        stages = [str(s) for s in (p.get("stages") or [])]
        current = p.get("current", 0) if isinstance(p.get("current", 0), int) else 0
        a = ((auto or {}).get("projects") or {}).get(pid) or {}
        if a.get("ok") and isinstance(a.get("current"), int) and a["current"] >= current:
            current = a["current"]
        result[pid] = {"id": pid, "name": str(p.get("name") or pid), "group": str(p.get("group") or ""),
                       "status": str(p.get("status") or ""), "stages": stages,
                       "current": max(0, min(current, len(stages) - 1)) if stages else 0}
    return result


# ---------------------------------------------------------------- подключение

def connect(path):
    """Подключение с обязательными настройками; каждая настройка читается обратно."""
    conn = sqlite3.connect(str(path), timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA recursive_triggers = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    mode = conn.execute("PRAGMA journal_mode = TRUNCATE").fetchone()[0]
    conn.execute("PRAGMA synchronous = FULL")
    got = (conn.execute("PRAGMA foreign_keys").fetchone()[0], conn.execute("PRAGMA recursive_triggers").fetchone()[0],
           str(mode).lower(), conn.execute("PRAGMA synchronous").fetchone()[0], conn.execute("PRAGMA busy_timeout").fetchone()[0])
    if got != (1, 1, "truncate", 2, 5000):
        conn.close()
        raise DayError(f"настройки базы плана дня не включились: {got}")
    return conn


def row_dict(row):
    return {k: row[k] for k in row.keys()}


# ---------------------------------------------------------------- хранилище

class Store:
    """Единственный писатель плана дня. Все изменения идут через apply() — и из окна Пульта, и из запросов Claude."""

    def __init__(self, folder, projects=None):
        self.folder = pathlib.Path(folder)
        self.db = self.folder / "day.db"
        self.export_path = self.folder / "day.json"
        self.inbox = self.folder / "day-inbox"
        self.applied = self.inbox / "applied"
        self.backups = self.folder / "day-plan-backups"
        self.projects = projects or (lambda: load_projects(self.folder))
        self.lock = threading.RLock()
        self.inbox_lock = threading.Lock()          # запросы Claude разбирает один поток за раз
        self.ready = False
        self.backed_up_on = None

    # -------- схема, резерв

    def open(self):
        """Открыть базу; при первом обращении — проверить версию, дошагать схему, сделать резерв за день."""
        conn = connect(self.db)
        if self.ready:
            return conn
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise DayError(f"day.db сделана более новой версией Пульта (схема {version}, эта программа знает {SCHEMA_VERSION}). "
                               "Обновите Пульт; базу не трогаю.")
            if version < SCHEMA_VERSION:
                if version > 0:
                    self.backup(conn, f"before-schema-v{version + 1}")
                for number in range(version + 1, SCHEMA_VERSION + 1):
                    try:
                        conn.executescript("BEGIN IMMEDIATE;\n" + MIGRATIONS[number - 1] +
                                           f"\nPRAGMA user_version = {number};\nCOMMIT;")
                    except sqlite3.Error:
                        if conn.in_transaction:
                            conn.execute("ROLLBACK")
                        raise
            problems = conn.execute("PRAGMA integrity_check").fetchall()
            if [tuple(r) for r in problems] != [("ok",)]:
                raise DayError("day.db повреждена: " + "; ".join(str(r[0]) for r in problems[:5]))
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise DayError("day.db: нарушены ссылки между задачами (foreign_key_check)")
            self.ready = True
        except Exception:
            conn.close()
            raise
        return conn

    def backup(self, conn, why="daily"):
        """Копия базы средствами SQLite в day-plan-backups. Старые копии не перезаписываются."""
        self.backups.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H%M%S")
        target = self.backups / f"day {stamp} {why}.db"
        n = 2
        while target.exists():
            target = self.backups / f"day {stamp} {why} ({n}).db"
            n += 1
        temporary = target.with_name(target.name + ".tmp")
        copy = sqlite3.connect(str(temporary))
        try:
            conn.backup(copy)
        finally:
            copy.close()
        os.replace(temporary, target)
        return target

    def daily_backup(self, conn):
        day = today_key()
        if self.backed_up_on == day:
            return None
        if self.backups.is_dir() and any(p.name.startswith(f"day {day} ") and p.suffix == ".db" for p in self.backups.iterdir()):
            self.backed_up_on = day
            return None
        if not conn.execute("SELECT 1 FROM items LIMIT 1").fetchone() and not conn.execute("SELECT 1 FROM day_notes LIMIT 1").fetchone():
            return None                      # пустую базу не копируем; проверим при следующей записи
        target = self.backup(conn)
        self.backed_up_on = day
        return target

    # -------- чтение

    def items_of(self, conn, day):
        rows = conn.execute("""SELECT i.*, t.day AS moved_to_day, f.day AS moved_from_day FROM items i
                               LEFT JOIN items t ON t.id = i.moved_to LEFT JOIN items f ON f.id = i.moved_from
                               WHERE i.day = ? ORDER BY i.position, i.created_at, i.id""", (day,)).fetchall()
        return [row_dict(r) for r in rows]

    def summary(self, conn, first, last):
        rows = conn.execute("SELECT day, status, count(*) AS n FROM items WHERE day BETWEEN ? AND ? GROUP BY day, status",
                            (first, last)).fetchall()
        days = {}
        for r in rows:
            days.setdefault(r["day"], dict.fromkeys(STATUSES, 0))[r["status"]] = r["n"]
        closes = {r["day"]: r for r in conn.execute("SELECT * FROM day_close WHERE day BETWEEN ? AND ?", (first, last)).fetchall()}
        notes = {r["day"]: r["note"] for r in conn.execute("SELECT day, note FROM day_notes WHERE day BETWEEN ? AND ?", (first, last)).fetchall()}
        out = []
        for day in sorted(set(days) | set(closes)):
            c = days.get(day) or dict.fromkeys(STATUSES, 0)
            planned = sum(c[s] for s in STATUSES if s != "removed")
            score = c["done"] + 0.5 * c["partial"]
            k = closes.get(day)
            out.append({"day": day, "counts": c, "total": planned, "left": c["planned"] + c["active"],
                        "percent": round(100 * score / planned) if planned else 0, "score": score,
                        "rating": k["rating"] if k else None, "closed": bool(k and k["closed"]),
                        "closed_at": k["closed_at"] if k else "", "note": notes.get(day, "")})
        return out

    def review(self, first, last):
        """Для вкладки «Итоги дней»: каждый день с планом или оценкой между first и last."""
        check_day(first, "с")
        check_day(last, "по")
        with self.lock:
            conn = self.open()
            try:
                return {"ok": True, "today": datetime.date.today().isoformat(), "from": first, "to": last,
                        "days": self.summary(conn, first, last)}
            finally:
                conn.close()

    def requests_tail(self, conn, limit=20):
        rows = conn.execute("SELECT name, at, ok, result FROM requests ORDER BY at DESC, name DESC LIMIT ?", (limit,)).fetchall()
        return [{"name": r["name"], "at": r["at"], "ok": bool(r["ok"]), "result": json.loads(r["result"])} for r in rows]

    def pending(self):
        try:
            return sorted(p.name for p in self.inbox.iterdir() if p.is_file() and p.suffix == ".json")
        except OSError:
            return []

    def view(self, day, around=30):
        """Всё для окна: задачи дня, заметка, итоги соседних дней, последние запросы Claude."""
        check_day(day)
        with self.lock:
            conn = self.open()
            try:
                note = conn.execute("SELECT note FROM day_notes WHERE day = ?", (day,)).fetchone()
                base = datetime.date.fromisoformat(day)
                t = datetime.date.today()
                first = min(base, t) - datetime.timedelta(days=around)
                last = max(base, t) + datetime.timedelta(days=around)
                close = conn.execute("SELECT rating, closed, closed_at FROM day_close WHERE day = ?", (day,)).fetchone()
                return {"ok": True, "day": day, "today": t.isoformat(), "note": note["note"] if note else "",
                        "close": row_dict(close) if close else None,
                        "items": self.items_of(conn, day), "summary": self.summary(conn, first.isoformat(), last.isoformat()),
                        "requests": self.requests_tail(conn, 10), "pending": len(self.pending()),
                        "schema": SCHEMA_VERSION, "sqlite": sqlite3.sqlite_version}
            finally:
                conn.close()

    def export(self, conn):
        """day.json — копия для чтения. Пишется после каждого изменения; сбой записи копии не ломает базу."""
        first = (datetime.date.today() - datetime.timedelta(days=EXPORT_DAYS_BACK)).isoformat()
        days = {}
        for r in conn.execute("SELECT DISTINCT day FROM items WHERE day >= ? UNION SELECT day FROM day_notes WHERE day >= ? "
                              "UNION SELECT day FROM day_close WHERE day >= ? ORDER BY 1", (first, first, first)).fetchall():
            note = conn.execute("SELECT note FROM day_notes WHERE day = ?", (r[0],)).fetchone()
            close = conn.execute("SELECT rating, closed, closed_at FROM day_close WHERE day = ?", (r[0],)).fetchone()
            days[r[0]] = {"note": note["note"] if note else "", "close": row_dict(close) if close else None,
                          "items": self.items_of(conn, r[0])}
        data = {"format": FORMAT, "about": "Копия плана дня для чтения. Подлинник — day.db; меняется только через Пульт "
                                           "(окно или запросы в day-inbox).",
                "written": now_text(), "today": today_key(), "schema": SCHEMA_VERSION, "sqlite": sqlite3.sqlite_version,
                "from": first, "days": days, "requests": self.requests_tail(conn, 50)}
        return write_atomic(self.export_path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")

    # -------- запись

    def apply(self, ops, by="pult"):
        """Применить список действий одной транзакцией: либо все, либо ни одного. Возвращает итоги действий."""
        if by not in BY:
            raise DayError(f"кто меняет: {by!r}")
        if not isinstance(ops, list) or not ops:
            raise DayError("нет действий")
        if len(ops) > MAX_OPS:
            raise DayError(f"слишком много действий за раз: {len(ops)} (предел {MAX_OPS})")
        projects = self.projects()
        with self.lock:
            conn = self.open()
            try:
                self.daily_backup(conn)
                conn.execute("BEGIN IMMEDIATE")
                try:
                    results = [self.one(conn, op, by, projects) for op in ops]
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                self.export(conn)
                return results
            except sqlite3.IntegrityError as exc:
                raise DayError(f"база не приняла изменение: {exc}")
            finally:
                conn.close()

    def log(self, conn, item, by, action, old, new):
        conn.execute("INSERT INTO item_log (item_id, at, by, action, old, new) VALUES (?, ?, ?, ?, ?, ?)",
                     (item, now_text(), by, action, None if old is None else str(old), None if new is None else str(new)))

    def item(self, conn, op):
        iid = op.get("id")
        if not isinstance(iid, str) or not ID_RE.match(iid):
            raise DayError(f"номер задачи: {iid!r}")
        row = conn.execute("SELECT * FROM items WHERE id = ?", (iid,)).fetchone()
        if not row:
            raise DayError(f"нет такой задачи: {iid}")
        return row

    def touch(self, conn, iid, **fields):
        names = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE items SET {names}, updated_at = ? WHERE id = ?", list(fields.values()) + [now_text(), iid])

    def one(self, conn, op, by, projects):
        if not isinstance(op, dict):
            raise DayError("действие должно быть объектом")
        name = op.get("op")
        handler = getattr(self, "op_" + name, None) if isinstance(name, str) and re.match(r"^[a-z_]+$", name) else None
        if not handler:
            raise DayError(f"неизвестное действие: {name!r}")
        return handler(conn, op, by, projects)

    def next_position(self, conn, day):
        return conn.execute("SELECT coalesce(max(position) + 1, 0) FROM items WHERE day = ?", (day,)).fetchone()[0]

    def op_add(self, conn, op, by, projects):
        day = check_day(op.get("day"))
        kind = op.get("kind")
        if kind not in KINDS:
            raise DayError(f"вид задачи: {kind!r} (нужно stage — завершить этап, advance — продвинуться, task — своя задача)")
        priority = op.get("priority") or "normal"
        if priority not in PRIORITIES:
            raise DayError(f"приоритет: {priority!r} (high, normal, low)")
        pid = op.get("project") or None
        project = None
        if pid is not None:
            project = projects.get(pid) if isinstance(pid, str) else None
            if not project:
                raise DayError(f"нет проекта {pid!r} на Пульте")
        if kind in ("stage", "advance") and not project:
            raise DayError("для «завершить этап» и «продвинуться» нужен проект")
        stage_index = stage_name = amount = None
        if kind == "stage":
            stages = project["stages"]
            if not stages:
                raise DayError(f"у проекта «{project['name']}» нет этапов")
            stage_index = op.get("stage", project["current"])
            if isinstance(stage_index, bool) or not isinstance(stage_index, int) or not 0 <= stage_index < len(stages):
                raise DayError(f"этап: номер от 0 до {len(stages) - 1}, а пришло {stage_index!r}")
            stage_name = one_line(stages[stage_index], "название этапа", 300)
            title = one_line(op.get("title"), "текст", 300, required=False) or stage_name
        elif kind == "advance":
            amount = one_line(op.get("amount"), "насколько продвинуться (например, «1 урок»)", 200)
            title = one_line(op.get("title"), "текст", 300, required=False) or amount
        else:
            title = one_line(op.get("title"), "текст задачи", 300)
        iid = op.get("id") or uuid.uuid4().hex
        if not isinstance(iid, str) or not ID_RE.match(iid):
            raise DayError(f"номер задачи: {iid!r} (32 знака 0-9a-f)")
        if conn.execute("SELECT 1 FROM items WHERE id = ?", (iid,)).fetchone():
            raise DayError(f"задача {iid} уже есть")
        position = op.get("position")
        if position is None:
            position = self.next_position(conn, day)
        else:
            if isinstance(position, bool) or not isinstance(position, int) or position < 0:
                raise DayError(f"место в очереди: {position!r}")
            conn.execute("UPDATE items SET position = position + 1 WHERE day = ? AND position >= ?", (day, position))
        stamp = now_text()
        conn.execute("""INSERT INTO items (id, day, position, priority, kind, project_id, project_name, stage_index, stage_name,
                        amount, title, status, note, moved_to, moved_from, added_by, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, NULL, NULL, ?, ?, ?)""",
                     (iid, day, position, priority, kind, pid, project["name"] if project else None, stage_index, stage_name,
                      amount, title, note_text(op.get("note")), by, stamp, stamp))
        self.log(conn, iid, by, "add", None, title)
        return {"op": "add", "id": iid, "day": day, "title": title}

    def op_plan(self, conn, op, by, projects):
        """План дня целиком: несколько задач сразу. replace=true — сначала убрать ещё не начатые задачи этого дня."""
        day = check_day(op.get("day"))
        items = op.get("items")
        if not isinstance(items, list) or not items:
            raise DayError("план: нужен список задач items")
        removed = []
        if op.get("replace"):
            for r in conn.execute("SELECT id FROM items WHERE day = ? AND status = 'planned'", (day,)).fetchall():
                self.touch(conn, r["id"], status="removed")
                self.log(conn, r["id"], by, "status", "planned", "removed")
                removed.append(r["id"])
        added = []
        for entry in items:
            if not isinstance(entry, dict):
                raise DayError("план: каждая задача — объект")
            added.append(self.op_add(conn, dict(entry, op="add", day=day), by, projects)["id"])
        return {"op": "plan", "day": day, "added": added, "removed": removed}

    def op_status(self, conn, op, by, projects):
        row = self.item(conn, op)
        status = op.get("status")
        if status not in SETTABLE:
            raise DayError(f"статус: {status!r} ({', '.join(SETTABLE)})")
        if row["status"] == "moved":
            raise DayError("задача уже перенесена в другой день — меняйте её там")
        if status != row["status"]:
            self.touch(conn, row["id"], status=status)
            self.log(conn, row["id"], by, "status", row["status"], status)
        if "note" in op:
            self.op_note(conn, {"id": row["id"], "note": op["note"]}, by, projects)
        return {"op": "status", "id": row["id"], "status": status}

    def op_remove(self, conn, op, by, projects):
        return self.op_status(conn, dict(op, status="removed"), by, projects)

    def op_restore(self, conn, op, by, projects):
        """Вернуть убранную задачу с тем статусом, который был до «убрать» (по журналу)."""
        row = self.item(conn, op)
        if row["status"] != "removed":
            raise DayError("вернуть можно только убранную задачу")
        last = conn.execute("""SELECT old FROM item_log WHERE item_id = ? AND action = 'status' AND new = 'removed'
                               ORDER BY n DESC LIMIT 1""", (row["id"],)).fetchone()
        before = last["old"] if last and last["old"] in SETTABLE and last["old"] != "removed" else "planned"
        return self.op_status(conn, dict(op, status=before), by, projects)

    def op_note(self, conn, op, by, projects):
        row = self.item(conn, op)
        note = note_text(op.get("note"))
        if note != row["note"]:
            self.touch(conn, row["id"], note=note)
            self.log(conn, row["id"], by, "note", row["note"], note)
        return {"op": "note", "id": row["id"]}

    def op_priority(self, conn, op, by, projects):
        row = self.item(conn, op)
        priority = op.get("priority")
        if priority not in PRIORITIES:
            raise DayError(f"приоритет: {priority!r} (high, normal, low)")
        if priority != row["priority"]:
            self.touch(conn, row["id"], priority=priority)
            self.log(conn, row["id"], by, "priority", row["priority"], priority)
        return {"op": "priority", "id": row["id"], "priority": priority}

    def op_edit(self, conn, op, by, projects):
        """Поправить текст, «насколько» или этап (для «завершить этап»). День, проект и вид не меняются."""
        row = self.item(conn, op)
        if row["status"] == "moved":
            raise DayError("задача уже перенесена в другой день — меняйте её там")
        fields = {}
        if row["kind"] == "stage" and "stage" in op:
            project = projects.get(row["project_id"])
            if not project:
                raise DayError("проекта этой задачи больше нет на Пульте — этап не поменять")
            idx = op["stage"]
            if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < len(project["stages"]):
                raise DayError(f"этап: номер от 0 до {len(project['stages']) - 1}")
            fields["stage_index"], fields["stage_name"] = idx, one_line(project["stages"][idx], "название этапа", 300)
            if row["title"] == row["stage_name"] and "title" not in op:
                fields["title"] = fields["stage_name"]
        if "amount" in op:
            if row["kind"] != "advance":
                raise DayError("«насколько» бывает только у задачи «продвинуться»")
            fields["amount"] = one_line(op["amount"], "насколько продвинуться", 200)
            if row["title"] == row["amount"] and "title" not in op:
                fields["title"] = fields["amount"]
        if "title" in op:
            fields["title"] = one_line(op["title"], "текст", 300)
        if not fields:
            raise DayError("нечего менять: title, amount или stage")
        old = {k: row[k] for k in fields}
        self.touch(conn, row["id"], **fields)
        self.log(conn, row["id"], by, "edit", json.dumps(old, ensure_ascii=False), json.dumps(fields, ensure_ascii=False))
        return {"op": "edit", "id": row["id"]}

    def op_order(self, conn, op, by, projects):
        """Новый порядок дня: ids — все видимые (не убранные и не перенесённые) задачи дня, в нужном порядке."""
        day = check_day(op.get("day"))
        ids = op.get("ids")
        if not isinstance(ids, list) or len(set(ids)) != len(ids or []):
            raise DayError("порядок: нужен список номеров без повторов")
        rows = conn.execute("SELECT id, position FROM items WHERE day = ? AND status NOT IN ('moved', 'removed')", (day,)).fetchall()
        have = {r["id"]: r["position"] for r in rows}
        if set(ids) != set(have):
            raise DayError("порядок устарел: в дне другие задачи — обновите вкладку и попробуйте ещё раз")
        for n, iid in enumerate(ids):
            if have[iid] != n:
                self.touch(conn, iid, position=n)
                self.log(conn, iid, by, "order", have[iid], n)
        return {"op": "order", "day": day}

    def op_carry(self, conn, op, by, projects):
        """«На завтра»: копия задачи в следующий день (не раньше сегодня), старая получает статус «перенесено»."""
        row = self.item(conn, op)
        if row["status"] not in OPEN:
            raise DayError(f"перенести можно незаконченную задачу, а эта — «{LABEL[row['status']]}»")
        day = datetime.date.fromisoformat(row["day"])
        target = op.get("to")
        if target is None:
            target = max(day + datetime.timedelta(days=1), datetime.date.today()).isoformat()
        else:
            check_day(target, "перенести на")
        if target <= row["day"]:
            raise DayError("перенести можно только на более поздний день")
        new = uuid.uuid4().hex
        stamp = now_text()
        conn.execute("""INSERT INTO items (id, day, position, priority, kind, project_id, project_name, stage_index, stage_name,
                        amount, title, status, note, moved_to, moved_from, added_by, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, NULL, ?, ?, ?, ?)""",
                     (new, target, self.next_position(conn, target), row["priority"], row["kind"], row["project_id"],
                      row["project_name"], row["stage_index"], row["stage_name"], row["amount"], row["title"], row["note"],
                      row["id"], by, stamp, stamp))
        self.touch(conn, row["id"], status="moved", moved_to=new)
        self.log(conn, row["id"], by, "carry", row["status"], target)
        self.log(conn, new, by, "add", None, f"перенесено с {row['day']}")
        return {"op": "carry", "id": row["id"], "new": new, "to": target}

    def op_day_note(self, conn, op, by, projects):
        day = check_day(op.get("day"))
        note = note_text(op.get("note"), 4000)
        if conn.execute("SELECT 1 FROM day_notes WHERE day = ?", (day,)).fetchone():
            conn.execute("UPDATE day_notes SET note = ?, updated_at = ? WHERE day = ?", (note, now_text(), day))
        else:
            conn.execute("INSERT INTO day_notes (day, note, updated_at) VALUES (?, ?, ?)", (day, note, now_text()))
        return {"op": "day_note", "day": day}

    def op_close_day(self, conn, op, by, projects):
        """«Закрыть день»: оценка от 1 до 10 (и, если есть, итог словами). Закрытый день можно закрыть снова с другой оценкой."""
        day = check_day(op.get("day"))
        rating = op.get("rating")
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 10:
            raise DayError(f"оценка дня: целое число от 1 до 10, а пришло {rating!r}")
        if "note" in op:
            self.op_day_note(conn, {"day": day, "note": op["note"]}, by, projects)
        stamp = now_text()
        row = conn.execute("SELECT * FROM day_close WHERE day = ?", (day,)).fetchone()
        if row:
            conn.execute("UPDATE day_close SET rating = ?, closed = 1, updated_at = ? WHERE day = ?", (rating, stamp, day))
            action = "rate" if row["closed"] else "close"
            old = row["rating"]
        else:
            conn.execute("INSERT INTO day_close (day, rating, closed, closed_at, updated_at) VALUES (?, ?, 1, ?, ?)", (day, rating, stamp, stamp))
            action, old = "close", None
        conn.execute("INSERT INTO day_log (day, at, by, action, old, new) VALUES (?, ?, ?, ?, ?, ?)",
                     (day, stamp, by, action, None if old is None else str(old), str(rating)))
        return {"op": "close_day", "day": day, "rating": rating}

    def op_reopen_day(self, conn, op, by, projects):
        day = check_day(op.get("day"))
        row = conn.execute("SELECT * FROM day_close WHERE day = ?", (day,)).fetchone()
        if not row or not row["closed"]:
            raise DayError("этот день не закрыт")
        stamp = now_text()
        conn.execute("UPDATE day_close SET closed = 0, updated_at = ? WHERE day = ?", (stamp, day))
        conn.execute("INSERT INTO day_log (day, at, by, action, old, new) VALUES (?, ?, ?, 'reopen', ?, NULL)",
                     (day, stamp, by, str(row["rating"])))
        return {"op": "reopen_day", "day": day}

    def op_carry_open(self, conn, op, by, projects):
        """Все незаконченные задачи дня — на следующий день (как «На завтра» у каждой)."""
        day = check_day(op.get("day"))
        ids = [r["id"] for r in conn.execute("SELECT id FROM items WHERE day = ? AND status IN ('planned', 'active', 'partial', 'not_done') "
                                             "ORDER BY position", (day,)).fetchall()]
        moved = [self.op_carry(conn, {"id": i, "to": op.get("to")} if op.get("to") else {"id": i}, by, projects) for i in ids]
        return {"op": "carry_open", "day": day, "moved": [m["new"] for m in moved]}

    # -------- запросы Claude

    def process_inbox(self):
        """Применить новые запросы из day-inbox/ (по порядку имён). Каждый запрос — одна транзакция.
        Итог — в day-inbox/applied/<имя>.result.json; сам запрос переносится туда же."""
        if not self.inbox_lock.acquire(blocking=False):
            return []                                # уже разбирает другой поток
        try:
            return self._process_inbox()
        finally:
            self.inbox_lock.release()

    def _process_inbox(self):
        done = []
        for name in self.pending():
            path = self.inbox / name
            try:
                st = path.stat()
            except OSError:
                continue
            outcome = None
            if not REQUEST_RE.match(name):
                outcome = {"ok": False, "error": "имя файла запроса: только латиница, цифры, точка, дефис, подчёркивание"}
            elif st.st_size > MAX_REQUEST:
                outcome = {"ok": False, "error": f"запрос больше {MAX_REQUEST // 1024} КБ"}
            else:
                try:
                    request = json.loads(path.read_text(encoding="utf-8-sig"))
                except (OSError, ValueError) as exc:
                    if time.time() - st.st_mtime < REQUEST_WAIT:
                        continue                          # возможно, ещё пишется — посмотрим в следующий раз
                    request, outcome = None, {"ok": False, "error": f"запрос не читается: {exc}"}
                if outcome is None:
                    outcome = self.apply_request(name, request)
            if outcome.get("ok") is False and not outcome.get("logged"):
                self.record(name, outcome)
            outcome.pop("logged", None)
            self.file_away(path, name, outcome)
            done.append(dict(outcome, name=name))
        return done

    def apply_request(self, name, request):
        with self.lock:
            conn = self.open()
            try:
                seen = conn.execute("SELECT ok, result FROM requests WHERE name = ?", (name,)).fetchone()
                if seen:
                    return dict(json.loads(seen["result"]), ok=bool(seen["ok"]), repeat=True, logged=True)
            finally:
                conn.close()
            try:
                if not isinstance(request, dict) or request.get("format") != FORMAT:
                    raise DayError(f"запрос: нужен объект с format = {FORMAT}")
                ops = request.get("ops")
                results = self.apply_with_record(name, ops)
                return {"ok": True, "results": results, "logged": True}
            except DayError as exc:
                return {"ok": False, "error": str(exc)}

    def apply_with_record(self, name, ops):
        """Как apply(), но в той же транзакции записывает запрос в журнал — повтор файла не применится дважды."""
        if not isinstance(ops, list) or not ops:
            raise DayError("нет действий")
        if len(ops) > MAX_OPS:
            raise DayError(f"слишком много действий за раз: {len(ops)} (предел {MAX_OPS})")
        projects = self.projects()
        conn = self.open()
        try:
            self.daily_backup(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                results = [self.one(conn, op, "claude", projects) for op in ops]
                conn.execute("INSERT INTO requests (name, at, ok, result) VALUES (?, ?, 1, ?)",
                             (name, now_text(), json.dumps({"results": results}, ensure_ascii=False)))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            self.export(conn)
            return results
        except sqlite3.IntegrityError as exc:
            raise DayError(f"база не приняла изменение: {exc}")
        finally:
            conn.close()

    def record(self, name, outcome):
        with self.lock:
            conn = self.open()
            try:
                if conn.execute("SELECT 1 FROM requests WHERE name = ?", (name,)).fetchone():
                    return
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("INSERT INTO requests (name, at, ok, result) VALUES (?, ?, 0, ?)",
                             (name[:125] if len(name) >= 6 else (name + "______")[:125], now_text(),
                              json.dumps({"error": outcome.get("error", "")}, ensure_ascii=False)))
                conn.execute("COMMIT")
                self.export(conn)
            finally:
                conn.close()

    def file_away(self, path, name, outcome):
        """Запрос — в applied/, рядом итог. Не получилось перенести — журнал запросов не даст применить его снова."""
        try:
            self.applied.mkdir(parents=True, exist_ok=True)
            write_atomic(self.applied / (name + ".result.json"),
                         json.dumps(dict(outcome, name=name, at=now_text()), ensure_ascii=False, indent=1) + "\n")
            target = self.applied / name
            if target.exists():
                target = self.applied / f"{name}.repeat-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            os.replace(path, target)
        except OSError:
            pass
