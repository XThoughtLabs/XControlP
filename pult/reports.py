# -*- coding: utf-8 -*-
"""XControlP — weekly and monthly reports. Moved unchanged from XControlP.pyw."""
import datetime
import json
import os
import pathlib
import re
import subprocess
from .config import (GIT_NO_WINDOW, HERE, MONTH_NAME, REPORT_MAX, REPORT_NAME, SOURCE)


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
