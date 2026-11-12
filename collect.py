# -*- coding: utf-8 -*-
"""Сборщик Пульта: по кнопке «Синхронизировать данные» читает продвижение проектов из их источников.

Что делает:
1. Берёт из projects.json проекты, у которых есть поле "source".
2. Для каждого такого проекта забирает свежие данные с GitHub (git fetch — рабочие файлы не трогает;
   у проекта с "fetch": false в source — не забирает, читает только данные на компьютере)
   и читает источник:
     "stages"  — файл этапов в репозитории (например, docs/stages.json) и слияния
                 веток этапов; этап засчитывается только по точному id (часть g2-0 — не весь G2);
     "lessons" — коды уроков в сообщениях коммитов курса (A17, H04, «Итог модуля A09-A12», «И-H ✅»,
                 по-английски «A21-A28 summary»);
     "progress" — файл продвижения PROGRESS.json в папке проекта без git (его ведёт исполнитель проекта).
3. Для раздела «Статистика» собирает по дням:
     уроки — дата первого коммита с кодом урока (курсы «lessons») или событие «Урок NN пройден»
             в файле продвижения (курсы «progress»);
     коммиты — во всех git-репозиториях папок, где лежат репозитории проектов (у CEO это GitHub):
             только число коммитов по дням (по времени автора, на часах этого компьютера), без текстов;
             один коммит в двух копиях репозитория считается один раз. Только чтение, без fetch.
4. Пишет итог в auto.json рядом с projects.json. Сам projects.json не меняется никогда.

Правила:
- этап двигает только источник; если по источнику этап меньше записанного вручную, этап не меняется,
  а в итоге появляется предупреждение;
- события пишутся только после даты "since" из projects.json (раньше история уже записана вручную);
- если GitHub недоступен, используются данные, которые уже есть на компьютере, и это видно в итоге;
- git только читает: без необязательных замков (GIT_OPTIONAL_LOCKS=0), в .git ничего не пишется, кроме fetch.

Проверка без Пульта:  python collect.py            (с git fetch)
                      python collect.py --no-fetch (только данные на компьютере)
"""
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "projects.json"
TARGET = HERE / "auto.json"

FETCH_TIMEOUT = 60      # секунд на один git fetch
GIT_TIMEOUT = 30        # секунд на чтение
NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # git без мигающих окон консоли

LESSON = re.compile(r"(?<![A-Za-zА-Яа-яЁё-])([A-Z])(\d{2})(?!\d)")
BLOCK = re.compile(r"^\s*([A-Z])(\d{2})\s*[–—-]\s*([A-Z])?(\d{2})")
SUMMARY_RANGE = re.compile(r"итог\s+модуля\s+([A-Z])(\d{2})\s*[–—-]\s*([A-Z])?(\d{2})", re.I)
# Итог блока по-английски: «A21-A28 summary», «Module A13-A20 summary», «summary of module A21–A28».
# Засчитывается только диапазон уроков рядом со словом summary; «A05 summary» блок не закрывает.
SUMMARY_RANGE_EN = (
    re.compile(r"(?<![A-Za-z])([A-Z])(\d{2})\s*[–—-]\s*([A-Z])?(\d{2})\s+summary\b", re.I),
    re.compile(r"\bsummary\s+(?:of\s+)?(?:(?:the\s+)?(?:module|block)\s+)?([A-Z])(\d{2})\s*[–—-]\s*([A-Z])?(\d{2})", re.I),
)
LESSON_EVENT = re.compile(r"^\s*Урок\s+([A-Z]?\d{1,3})\s+пройден", re.I)    # «Урок 06 пройден: …» в PROGRESS.json
STATS_DAYS = 400        # коммиты для статистики — за последние 400 дней (год и квартал с запасом)
SUMMARY_LETTER = re.compile(r"(?<![A-Za-zА-Яа-яЁё])И-([A-Z])\b[^\n]*?✅")
STAGE_TOKEN = re.compile(r"stage[-_\s]+([a-z0-9]+(?:-[a-z0-9]+)*)", re.I)   # «stage-g2-0-text-store», «stage g2-0r2»


class SourceError(Exception):
    pass


# ---------------------------------------------------------------- git

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


def git(repo, *args, timeout=GIT_TIMEOUT):
    exe = git_exe()
    if not exe:
        raise SourceError("Git не найден на компьютере")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_OPTIONAL_LOCKS="0", LC_ALL="C.UTF-8")
    try:
        done = subprocess.run(
            [exe, "-C", str(repo), "-c", "core.quotepath=off", "-c", "i18n.logOutputEncoding=UTF-8", *args],
            capture_output=True, timeout=timeout, env=env, creationflags=NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        raise SourceError("git не ответил за " + str(timeout) + " с")
    if done.returncode != 0:
        message = done.stderr.decode("utf-8", "replace").strip().splitlines()
        raise SourceError(message[-1] if message else "git завершился с ошибкой")
    return done.stdout.decode("utf-8", "replace")


def main_ref(repo):
    for ref in ("origin/HEAD", "origin/main", "origin/master", "main", "master", "HEAD"):   # без origin — своя main
        try:
            git(repo, "rev-parse", "--verify", "-q", ref + "^{commit}")
            return ref
        except SourceError:
            continue
    raise SourceError("в репозитории не найдена основная ветка")


def activity(repo):
    """Самый свежий коммит среди своих веток и веток на GitHub: дата, ветка, текст."""
    out = git(repo, "for-each-ref", "--sort=-committerdate", "--count=1",
              "--format=%(committerdate:short)%09%(refname:short)%09%(subject)", "refs/heads", "refs/remotes")
    line = out.strip().splitlines()
    if not line:
        return None
    date, branch, subject = (line[0].split("\t") + ["", "", ""])[:3]
    return {"date": date, "branch": branch, "text": subject}


# ---------------------------------------------------------------- источники

def stage_key(label):
    """«G1b: запись» → «g1b»."""
    return label.split(":", 1)[0].strip().lower()


def stage_id_in(text, known, token=STAGE_TOKEN):
    """Id этапа в имени ветки или в тексте слияния — только точный и только из списка known.

    «…/stage-g2-0-text-store» → «g2-0»; «merge stage g2-0r2 (…)» → «g2-0r2».
    Id подходит, если за ним конец или «-» и слово с буквы: в «g2-0-text-store» нет id «g2»
    (после «g2-» идёт цифра). Из подходящих берётся самый длинный. Неизвестный id — None.
    """
    for m in token.finditer(text):
        word = m[1].lower()
        found = None
        for key in known:
            if word == key or (word.startswith(key + "-") and word[len(key) + 1:len(key) + 2].isalpha()):
                if found is None or len(key) > len(found):
                    found = key
        if found:
            return found
    return None


def read_stages(repo, ref, source, stages):
    """Этап по двум свидетельствам: файл этапов в основной ветке и слияния веток этапов в неё.

    Файл этапов (stages.json) отмечает слияние только в следующем этапе, поэтому слияние ветки
    вида «…/stage-g1a-…» в основную ветку засчитывается сразу. Ветка этапа, ещё не слитая, —
    этап в работе. Этап засчитывается только по точному id, который есть и на Пульте, и в файле
    этапов: часть «g2-0» не засчитывается как «g2». Этапы файла, которых нет на Пульте
    (с даты since), возвращаются списком — для предупреждения.
    """
    index = {stage_key(s): i for i, s in enumerate(stages)}
    pattern = source.get("branch_pattern")
    token = re.compile(pattern, re.I) if pattern else STAGE_TOKEN
    since = source.get("since", "")
    merged, started, in_file, unknown = {}, {}, set(), []

    path = source.get("file", "")
    if path:
        try:
            data = json.loads(git(repo, "show", ref + ":" + path))
        except (SourceError, ValueError) as exc:
            raise SourceError("файл этапов не читается: " + str(exc))
        items = data.get("stages") if isinstance(data, dict) else data
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("id", "")).strip().lower()
            if not key:
                continue
            in_file.add(key)
            if key not in index:
                if str(item.get("date", "")) >= since and key not in unknown:
                    unknown.append(key)
                continue
            if item.get("merge_commit"):
                try:
                    date = git(repo, "show", "-s", "--format=%cs", item["merge_commit"]).strip()
                except SourceError:
                    date = ""
                merged[key] = date or item.get("date", "")
            else:
                started.setdefault(key, item.get("date", ""))

    known = [k for k in index if k in in_file] if in_file else list(index)

    for line in git(repo, "log", ref, "--merges", "--format=%cs%x09%s").splitlines():
        date, _, subject = line.partition("\t")
        key = stage_id_in(subject, known, token)
        if key:
            merged[key] = min(date, merged.get(key) or date)

    refs = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes").split()
    for name in refs:
        key = stage_id_in(name, known, token)
        if not key or key in merged:
            continue
        first = git(repo, "log", ref + ".." + name, "--reverse", "--format=%cs").split()
        if first:
            started[key] = min(first[0], started.get(key) or first[0])

    if not merged and not started:
        raise SourceError("ни один этап из источника не совпал с этапами Пульта")
    current = max((index[k] for k in merged), default=-1) + 1
    current = min(current, len(stages) - 1)
    events = [{"date": d, "text": "Слит " + stages[index[k]]} for k, d in merged.items()]
    events += [{"date": d, "text": "Начат " + stages[index[k]]} for k, d in started.items() if k not in merged]
    dates = [d for k, d in merged.items() if index[k] == current - 1] + \
            [d for k, d in started.items() if index[k] == current and k not in merged]
    return current, max(dates) if dates else None, sorted(events, key=lambda e: e["date"]), unknown


def blocks_of(stages):
    """Этапы курса вида «A13–A20: …» → (номер этапа, буква, от, до)."""
    out = []
    for i, label in enumerate(stages):
        m = BLOCK.match(label)
        if m:
            out.append((i, m[1], int(m[2]), int(m[4])))
    return out


def block_of(blocks, letter, number):
    for i, l, lo, hi in blocks:
        if l == letter and lo <= number <= hi:
            return i
    return None


def read_lessons(repo, ref, stages):
    blocks = blocks_of(stages)
    if not blocks:
        raise SourceError("в этапах Пульта нет блоков вида «A01–A08»")
    log = git(repo, "log", ref, "--reverse", "--format=%cs%x09%at%x09%s")
    reached, move, events, seen = 0, None, [], {}
    for line in log.splitlines():
        date, _, rest = line.partition("\t")
        stamp, _, subject = rest.partition("\t")
        # день урока для статистики — по времени автора на часах этого компьютера (как у коммитов);
        # события этапов — по дате коммита, как раньше
        day = datetime.date.fromtimestamp(int(stamp)).isoformat() if stamp.isdigit() else date
        closed = set()
        m = SUMMARY_RANGE.search(subject) or next((x for x in (rx.search(subject) for rx in SUMMARY_RANGE_EN) if x), None)
        if m:
            b = block_of(blocks, m[1].upper(), int(m[2]))
            if b is not None:
                closed.add(b)
        m = SUMMARY_LETTER.search(subject)
        if m:
            first = [i for i, l, lo, hi in blocks if l == m[1]]
            closed.update(first[-1:])           # модуль закрыт — последний блок этой буквы
        before = reached
        for letter, number in LESSON.findall(subject):
            b = block_of(blocks, letter, int(number))
            if b is not None:
                code = letter + number                      # урок — по первому коммиту с его кодом
                seen[code] = min(day, seen.get(code) or day)
            if b is not None and b > reached:
                reached = b
        for b in sorted(closed):
            if b + 1 > reached:
                events.append({"date": date, "text": "Пройден блок " + stages[b]})
                reached = min(b + 1, len(stages) - 1)
        if reached > before:
            move = date
            if not closed:
                events.append({"date": date, "text": "Начат блок " + stages[reached]})
    lessons = [{"code": code, "date": date} for code, date in seen.items()]
    return reached, move, events, sorted(lessons, key=lambda x: (x["date"], x["code"]))


def lessons_of_events(events):
    """Уроки курса из файла продвижения: событие «Урок 06 пройден: …» → {"code": "06", "date": …} (первое по дате)."""
    seen = {}
    for e in sorted(events, key=lambda x: x["date"]):
        m = LESSON_EVENT.match(e["text"])
        if m:
            seen.setdefault(m[1].upper(), e["date"])
    return [{"code": code, "date": date} for code, date in seen.items()]


def same_label(a, b):
    norm = lambda x: re.sub(r"\s+", " ", str(x).replace("—", "–").replace("-", "–")).strip().lower()
    return norm(a) == norm(b)


def read_progress(path, stages):
    """PROGRESS.json в папке проекта: этапы (как на Пульте), текущий этап, дата его смены, события."""
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
        changed = datetime.date.fromtimestamp(pathlib.Path(path).stat().st_mtime).isoformat()
    except FileNotFoundError:
        raise SourceError("файл продвижения ещё не создан: " + str(path))
    except (OSError, ValueError) as exc:
        raise SourceError("файл продвижения не читается: " + str(exc))
    listed = data.get("stages") or []
    if len(listed) != len(stages) or not all(same_label(a, b) for a, b in zip(listed, stages)):
        raise SourceError("этапы в файле продвижения не совпадают с этапами Пульта")
    current = data.get("current")
    if not isinstance(current, int) or not 0 <= current < len(stages):
        raise SourceError("в файле продвижения нет правильного номера текущего этапа (current)")
    events = [{"date": str(e.get("date", "")), "text": str(e.get("text", ""))}
              for e in data.get("events") or [] if isinstance(e, dict) and e.get("date") and e.get("text")]
    last = max([changed] + [e["date"] for e in events])
    activity = {"date": last, "branch": "", "text": str(data.get("now") or "файл продвижения обновлён")}
    return current, data.get("stage_changed") or None, events, activity


# ---------------------------------------------------------------- один проект

def collect_project(project, fetch, path_map):
    source = project["source"]
    name = project.get("name", project.get("id"))
    result = {"ok": False, "name": name, "kind": source.get("kind", "")}
    notes = []
    if source.get("kind") == "progress":
        try:
            current, move, events, act = read_progress(remap(source.get("path", ""), path_map), project.get("stages") or [])
        except SourceError as exc:
            result["error"] = str(exc)
            return result, notes
        result["activity"] = act
        lessons = lessons_of_events(events)
        if lessons:
            result["lessons"] = lessons
        return finish(project, source, result, notes, current, move, events, ref="")
    repo = pathlib.Path(remap(source.get("repo", ""), path_map))
    if not (repo / ".git").exists():
        result["error"] = "нет репозитория: " + str(repo)
        return result, notes
    if source.get("fetch", True) is False:
        result["local_only"] = True          # у проекта fetch выключен: только данные на компьютере
    elif fetch:
        try:
            git(repo, "fetch", "--quiet", "--no-tags", "origin", timeout=FETCH_TIMEOUT)
            result["fetched"] = True
        except SourceError as exc:
            result["fetched"] = False
            notes.append(name + ": не удалось взять свежее с GitHub (" + str(exc) + ") — использованы данные с компьютера")
    try:
        ref = main_ref(repo)
        stages = project.get("stages") or []
        kind = source.get("kind")
        if kind == "stages":
            current, move, events, unknown = read_stages(repo, ref, source, stages)
            if unknown:
                notes.append(name + ": в " + source.get("file", "файле этапов") + " есть этапы, которых нет на Пульте: " +
                             ", ".join(unknown) + " — добавить их в projects.json")
        elif kind == "lessons":
            current, move, events, result["lessons"] = read_lessons(repo, ref, stages)
        else:
            raise SourceError("неизвестный вид источника: " + str(kind))
        result["activity"] = activity(repo)
    except SourceError as exc:
        result["error"] = str(exc)
        return result, notes

    return finish(project, source, result, notes, current, move, events, ref)


def finish(project, source, result, notes, current, move, events, ref):
    name = result["name"]
    stages = project.get("stages") or []
    since = source.get("since", "")
    manual = project.get("current", 0)
    result.update(ok=True, ref=ref, source_current=current,
                  events=[e for e in events if e["date"] and e["date"] > since])
    if current < manual:
        result["current"] = manual
        notes.append(name + ": по источнику этап «" + stages[current] + "», а в projects.json уже «" + stages[manual] +
                     "» — оставлен записанный вручную")
    else:
        result["current"] = current
        if move:
            result["last_move"] = move
    result["stage"] = stages[result["current"]] if stages else ""
    return result, notes


def remap(path, path_map):
    for src, dst in path_map:
        if path.lower().startswith(src.lower()):
            rest = path[len(src):].replace("\\", "/").lstrip("/")
            return str(pathlib.Path(dst) / rest)
    return path


# ---------------------------------------------------------------- статистика

def same_path(a, b):
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def commit_stats(projects, path_map):
    """Коммиты по дням во всех git-репозиториях папок, где лежат репозитории проектов.

    Только чтение: git log по веткам, веткам GitHub и меткам (без stash), без fetch и без замков.
    Дата — по времени автора, на часах этого компьютера. Тексты коммитов не берутся.
    Один и тот же коммит (две копии репозитория, worktree) считается один раз — у репозитория проекта.
    """
    roots, linked = [], []
    for p in projects:
        src = p.get("source") if isinstance(p.get("source"), dict) else {}
        if not src.get("repo"):
            continue
        repo = pathlib.Path(remap(src["repo"], path_map))
        linked.append((repo, p.get("id")))
        if not any(same_path(repo.parent, r) for r in roots):
            roots.append(repo.parent)
    since = (datetime.date.today() - datetime.timedelta(days=STATS_DAYS)).isoformat()
    found, errors = [], []
    for root in roots:
        try:
            children = sorted((d for d in root.iterdir() if d.is_dir()), key=lambda d: d.name.lower())
        except OSError as exc:
            errors.append(str(root) + ": " + (exc.strerror or str(exc)))
            continue
        found += [d for d in children if (d / ".git").exists()]
    project_of = lambda d: next((pid for repo, pid in linked if same_path(repo, d)), None)
    found.sort(key=lambda d: (project_of(d) is None, d.name.lower()))   # репозитории проектов — первыми
    seen, repos = set(), []
    for repo in found:
        try:
            log = git(repo, "log", "--branches", "--remotes", "--tags", "--since=" + since, "--format=%H %at")
        except SourceError as exc:
            if "does not have any commits" not in str(exc):
                errors.append(repo.name + ": " + str(exc))
            continue
        days = {}
        for line in log.splitlines():
            sha, _, stamp = line.partition(" ")
            if not stamp.strip().isdigit() or sha in seen:
                continue
            seen.add(sha)
            day = datetime.date.fromtimestamp(int(stamp)).isoformat()
            if day >= since:
                days[day] = days.get(day, 0) + 1
        repos.append({"name": repo.name, "project": project_of(repo), "days": dict(sorted(days.items()))})
    return {"since": since, "roots": [str(r) for r in roots], "repos": repos, "errors": errors}


# ---------------------------------------------------------------- всё вместе

def collect(fetch=True, path_map=()):
    data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    started = datetime.datetime.now()
    out = {"synced": started.strftime("%Y-%m-%d %H:%M"), "projects": {}, "notes": [], "errors": []}
    lessons = {}
    for project in data.get("projects", []):
        if not isinstance(project.get("source"), dict):
            continue
        result, notes = collect_project(project, fetch, path_map)
        out["projects"][project["id"]] = result
        out["notes"].extend(notes)
        if not result["ok"]:
            out["errors"].append(result["name"] + ": " + result.get("error", "ошибка"))
        if result.get("lessons"):
            lessons[project["id"]] = result.pop("lessons")
    try:
        commits = commit_stats(data.get("projects", []), path_map)
    except Exception as exc:                 # статистика не должна ломать синхронизацию
        commits = {"repos": [], "errors": [type(exc).__name__ + ": " + str(exc)]}
    out["stats"] = {"lessons": lessons, "commits": commits}
    out["seconds"] = round((datetime.datetime.now() - started).total_seconds(), 1)
    temporary = TARGET.with_name("auto.json." + str(os.getpid()) + ".tmp")
    temporary.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporary, TARGET)
    return out


def main():
    fetch = "--no-fetch" not in sys.argv
    path_map = []
    for arg in sys.argv[1:]:
        if arg.startswith("--map="):                  # для проверки на другой машине: --map=C:\Users\<user>\GitHub=/путь
            src, _, dst = arg[len("--map="):].partition("=")
            path_map.append((src, dst))
    out = collect(fetch, path_map)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
