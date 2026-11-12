# -*- coding: utf-8 -*-
"""Сводки Пульта: ежедневные сводки новостей из git-репозитория сводок.

Репозиторий: путь, который передаёт Пульт (ключ digest_repo в projects.json), или переменная PULT_DIGEST_REPO.
Репозитория по умолчанию нет: не задан — раздел «Сводки» пуст и ни одна команда git не запускается.
- digests/ГГГГ/ММ/ГГГГ-ММ-ДД.json — сводка дня (её кладёт утренняя задача Claude), рядом .md для чтения.
- marks/ГГГГ/ММ/ГГГГ-ММ-ДД.json — отметки «интересно» и «полезно» к пунктам этой сводки.
  Их пишет только эта программа и сразу делает коммит и push.
  Нет сети — коммит остаётся на компьютере и уходит при следующей отметке или синхронизации.
- Кнопка «Синхронизировать данные»: git pull --rebase (новые сводки), затем push неотправленных отметок.
Сводки и отметки лежат в разных файлах, поэтому коммиты задачи и Пульта друг другу не мешают.
"""
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import threading

TOPICS = {"llm-models": "Модели", "llm-research": "Исследования и продукты", "agents-memory": "Агенты и память",
          "security-storage": "Утечки и защита", "hardware": "Железо"}
KINDS = ("interesting", "useful")
KIND_NAME = {"interesting": "интересно", "useful": "полезно"}
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
KEEP_DAYS = 400                 # в окне — сводки за последние 400 дней
NET_TIMEOUT = 60                # секунд на pull и push
NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # git без мигающих окон консоли


class DigestError(Exception):
    pass


def git_exe():
    exe = shutil.which("git")
    if exe:
        return exe
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            for tail in (r"Git\cmd\git.exe", r"Programs\Git\cmd\git.exe"):
                path = pathlib.Path(base) / tail
                if path.is_file():
                    return str(path)
    return None


def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


class Digests:
    def __init__(self, repo=None):
        value = str(repo or os.environ.get("PULT_DIGEST_REPO") or "").strip()
        self.repo = pathlib.Path(os.path.expanduser(value)) if value else None   # None — сводки не настроены
        self.lock = threading.RLock()        # отметки, коммиты, pull и push — по одному
        self.last_push = {"ok": None, "at": "", "error": ""}

    # ------------------------------------------------------------ git

    def git(self, *args, timeout=30):
        if self.repo is None:
            raise DigestError("репозиторий сводок не задан")
        exe = git_exe()
        if not exe:
            raise DigestError("Git не найден на компьютере")
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", LC_ALL="C.UTF-8")
        try:
            done = subprocess.run([exe, "-C", str(self.repo), "-c", "core.quotepath=off", *args],
                                  capture_output=True, timeout=timeout, env=env, creationflags=NO_WINDOW)
        except subprocess.TimeoutExpired:
            raise DigestError("git не ответил за " + str(timeout) + " с")
        if done.returncode != 0:
            lines = done.stderr.decode("utf-8", "replace").strip().splitlines() or done.stdout.decode("utf-8", "replace").strip().splitlines()
            raise DigestError(lines[-1] if lines else "git завершился с ошибкой")
        return done.stdout.decode("utf-8", "replace")

    def exists(self):
        return self.repo is not None and (self.repo / ".git").exists()

    # ------------------------------------------------------------ чтение

    def files(self, folder):
        """[(дата, путь)] файлов folder/ГГГГ/ММ/ГГГГ-ММ-ДД.json, сначала новые."""
        found = []
        if self.repo is None:
            return found
        base = self.repo / folder
        if base.is_dir():
            for path in base.glob("*/*/*.json"):
                m = DATE_RE.match(path.stem)
                if m and path.parent.name == m.group(2) and path.parent.parent.name == m.group(1):
                    found.append((path.stem, path))
        return sorted(found, reverse=True)

    def digest_path(self, date):
        return self.repo / "digests" / date[:4] / date[5:7] / (date + ".json")

    def marks_path(self, date):
        return self.repo / "marks" / date[:4] / date[5:7] / (date + ".json")

    def stamp(self):
        """Что изменилось в репозитории (сводки, отметки, итог последней отправки) — для пересборки data.js."""
        result = []
        for folder in ("digests", "marks"):
            for date, path in self.files(folder):
                try:
                    st = path.stat()
                    result.append((folder, date, st.st_mtime_ns, st.st_size))
                except OSError:
                    pass
        return tuple(result) + (self.last_push.get("at", ""), self.last_push.get("ok"))

    def read_marks(self, date):
        try:
            raw = json.loads(self.marks_path(date).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return {}
        marks = raw.get("marks") if isinstance(raw, dict) else None
        if not isinstance(marks, dict):
            return {}
        result = {}
        for key, value in marks.items():
            if isinstance(key, str) and isinstance(value, dict):
                entry = {kind: bool(value.get(kind)) for kind in KINDS}
                entry["at"] = str(value.get("at", ""))
                result[key] = entry
        return result

    @staticmethod
    def item(raw, date, number):
        if not isinstance(raw, dict):
            return None
        text = lambda key: str(raw.get(key) or "").strip()
        url = text("url")
        published = text("published")
        # Перевод (с 31.10.2026): i18n.en / i18n.he — те же три поля; русский остаётся оригиналом.
        tr = {}
        raw_tr = raw.get("i18n")
        if isinstance(raw_tr, dict):
            for lang in ("en", "he"):
                part = raw_tr.get(lang)
                if isinstance(part, dict):
                    fields = {k: str(part.get(k) or "").strip() for k in ("title", "summary", "why")}
                    if any(fields.values()):
                        tr[lang] = fields
        return {"id": text("id") or "%s-%02d" % (date, number), "topic": text("topic") if text("topic") in TOPICS else "",
                "title": text("title"), "summary": text("summary"), "why": text("why"),
                "url": url if url.startswith("https://") else "", "source": text("source"),
                "published": published if DATE_RE.match(published) else "", "i18n": tr}

    def view(self):
        """Всё для окна: сводки (сначала новые) с отметками, ошибки чтения, состояние отправки на GitHub."""
        result = {"ok": False, "error": "", "repo": str(self.repo or ""), "topics": TOPICS, "digests": [],
                  "push": dict(self.last_push), "unpushed": None}
        if self.repo is None:
            return result                    # не настроено: пустой раздел, без git
        if not self.exists():
            result["error"] = "Нет репозитория сводок: " + str(self.repo)
            return result
        oldest = (datetime.date.today() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
        for date, path in self.files("digests"):
            if date < oldest:
                break
            try:
                raw = json.loads(path.read_text(encoding="utf-8-sig"))
                if not isinstance(raw, dict):
                    raise ValueError("ожидался объект JSON")
            except (OSError, ValueError) as exc:
                result["digests"].append({"date": date, "error": "Файл сводки не читается: " + str(exc),
                                          "items": [], "unverified": [], "marks": {}})
                continue
            items = [it for it in (self.item(x, date, i + 1) for i, x in enumerate(raw.get("items") or [])) if it and it["title"]]
            unverified = [str(u).strip() for u in (raw.get("unverified") or []) if str(u).strip()]
            unverified_tr = {}
            raw_u = raw.get("unverified_i18n")
            if isinstance(raw_u, dict):
                for lang in ("en", "he"):
                    lines = raw_u.get(lang)
                    if isinstance(lines, list) and len([x for x in lines if str(x).strip()]) == len(unverified):
                        unverified_tr[lang] = [str(x).strip() for x in lines if str(x).strip()]
            result["digests"].append({"date": date, "generated_at": str(raw.get("generated_at") or ""), "error": "",
                                      "items": items, "unverified": unverified, "unverified_i18n": unverified_tr,
                                      "marks": self.read_marks(date)})
        try:
            result["unpushed"] = int(self.git("rev-list", "--count", "@{u}..HEAD").strip() or 0)
        except DigestError:
            result["unpushed"] = None
        result["ok"] = True
        return result

    # ------------------------------------------------------------ отметки и обмен с GitHub

    def mark(self, date, item, kind, value):
        """Отметка к пункту сводки: файл отметок → коммит → отправка на GitHub в фоне."""
        if self.repo is None:
            raise DigestError("репозиторий сводок не задан")
        if not DATE_RE.match(date or ""):
            raise DigestError("нет даты сводки")
        if kind not in KINDS:
            raise DigestError("неизвестная отметка: %r" % kind)
        try:
            raw = json.loads(self.digest_path(date).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            raise DigestError("нет сводки на " + date)
        ids = {str(x.get("id")) for x in (raw.get("items") or []) if isinstance(x, dict)}
        if item not in ids:
            raise DigestError("в сводке на %s нет пункта %s" % (date, item))
        value = bool(value)
        with self.lock:
            marks = self.read_marks(date)
            entry = marks.get(item) or {kind_: False for kind_ in KINDS}
            if bool(entry.get(kind)) == value:
                return {"ok": True, "changed": False}
            entry = {kind_: bool(entry.get(kind_)) for kind_ in KINDS}
            entry[kind] = value
            entry["at"] = now_text()
            marks[item] = entry
            path = self.marks_path(date)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
            temporary.write_text(json.dumps({"date": date, "marks": dict(sorted(marks.items()))}, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
            os.replace(temporary, path)
            rel = path.relative_to(self.repo).as_posix()
            self.git("add", "--", rel)
            self.git("commit", "-q", "-m", "Отметка %s: %s — %s" % (item, KIND_NAME[kind], "да" if value else "нет"), "--", rel)
        threading.Thread(target=self.push, daemon=True).start()
        return {"ok": True, "changed": True}

    def push(self):
        """git pull --rebase (забрать новые сводки) и push неотправленных отметок."""
        if self.repo is None:
            return {"ok": False, "at": now_text(), "error": "репозиторий сводок не задан"}
        with self.lock:
            try:
                self.git("pull", "-q", "--rebase", timeout=NET_TIMEOUT)
                ahead = int(self.git("rev-list", "--count", "@{u}..HEAD").strip() or 0)
                if ahead:
                    self.git("push", "-q", timeout=NET_TIMEOUT)
                self.last_push = {"ok": True, "at": now_text(), "error": ""}
            except DigestError as exc:
                git_dir = self.repo / ".git"
                if (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
                    try:
                        self.git("rebase", "--abort")
                    except DigestError:
                        pass
                self.last_push = {"ok": False, "at": now_text(), "error": str(exc)}
            return dict(self.last_push)

    def sync(self):
        """Кнопка «Синхронизировать данные»: новые сводки с GitHub и отправка отметок."""
        if self.repo is None:
            return {"ok": False, "error": "", "new": 0, "total": 0}
        if not self.exists():
            return {"ok": False, "error": "Нет репозитория сводок: " + str(self.repo), "new": 0, "total": 0}
        before = {date for date, _ in self.files("digests")}
        result = self.push()
        after = {date for date, _ in self.files("digests")}
        return {"ok": bool(result["ok"]), "error": result["error"], "new": len(after - before), "total": len(after)}
