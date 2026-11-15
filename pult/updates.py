# -*- coding: utf-8 -*-
"""XControlP — the update check: is there a newer version of the program on GitHub, and updating it.

Off by default (the setting «updates» in settings.json). While it is off, no git command runs.
When it is on, the check runs in the background at start and at «Синхронизировать данные»:
git fetch of the branch the program's folder follows (a fork: the remote «upstream», if there is one),
then a count of the commits on each side. Updating runs only on the user's click, only as a
fast-forward, only when no tracked file of the program has local changes. Data files are not tracked
by git (most are ignored), but a fast-forward would still replace an ignored file when the update brings
a file at its path or a folder in its place. So the update first lists such files of the user's and
refuses, naming them; and the merge itself runs with --no-overwrite-ignore, so git refuses as well.
After an update the program asks to be restarted."""
import datetime
import os
import re
import shutil
import subprocess
import threading
from .config import (GIT_NO_WINDOW, HERE)

FETCH_TIMEOUT = 30        # seconds for git fetch (the network)
LOCAL_TIMEOUT = 10        # seconds for every other git command
# a branch or remote name the check accepts: no option-like or unusual names reach git
NAME = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._/-]{0,199}")
STATES = ("off", "checking", "current", "available", "ahead", "diverged", "unavailable", "error", "updated")

_LOCK = threading.Lock()          # one check or update at a time
_STATE = {"state": "off", "behind": 0, "ahead": 0, "source": "", "error": "", "checked": "", "restart": False, "version": 0}
_STAMP = [0]                      # grows on every change of the state: data.js is rebuilt


class UpdateError(Exception):
    """A git command failed or did not answer; the text is shown in the window. lines: git's whole message."""

    def __init__(self, text, lines=()):
        super().__init__(text)
        self.lines = list(lines)


def git_exe():
    return shutil.which("git")


def git(root, *args, timeout=LOCAL_TIMEOUT):
    """One git command in the program's folder, its output as text (trimmed)."""
    return git_raw(root, *args, timeout=timeout).decode("utf-8", "replace").strip()


def git_raw(root, *args, timeout=LOCAL_TIMEOUT):
    """One git command in the program's folder, its output as bytes, untouched (file names stay exactly as on
    disk: no trimmed spaces, no replaced bytes). Never asks for a password, never opens a window."""
    exe = git_exe()
    if not exe:
        raise UpdateError("git не найден")
    # a stalled transfer is stopped by git itself (under 1000 bytes/s for 20 s), not only by the time limit
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", LC_ALL="C",
               GIT_HTTP_LOW_SPEED_LIMIT="1000", GIT_HTTP_LOW_SPEED_TIME="20")
    try:
        done = subprocess.run([exe, "-C", str(root)] + list(args), capture_output=True, timeout=timeout,
                              env=env, creationflags=GIT_NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise UpdateError("git не ответил за " + str(timeout) + " с")
    except OSError as exc:
        raise UpdateError(f"git не запустился: {exc}")
    if done.returncode != 0:
        text = (done.stderr or done.stdout or b"").decode("utf-8", "replace").strip().splitlines()
        raise UpdateError(text[-1] if text else "git: код " + str(done.returncode), text)
    return done.stdout


def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")


def update_source(root):
    """Where updates come from: (remote, branch, ref), or a text saying why there is no source.
    The branch is the current one; a remote named «upstream» (a fork's original) wins over the
    branch's own upstream (usually origin)."""
    if not (root / ".git").exists():
        return None, "папка программы — не клон git"
    if not git_exe():
        return None, "git не найден"
    try:
        branch = git(root, "symbolic-ref", "-q", "--short", "HEAD")
    except UpdateError:
        return None, "программа не на ветке"
    if not NAME.fullmatch(branch):
        return None, "необычное имя ветки — проверка не запускается"
    remotes = git(root, "remote").split()
    if "upstream" in remotes:
        return ("upstream", branch, "upstream/" + branch), ""
    try:
        tracked = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    except UpdateError:
        return None, "у ветки " + branch + " нет удалённой ветки"
    remote, _, rbranch = tracked.partition("/")
    if not remote or not rbranch or remote not in remotes:
        return None, "у ветки " + branch + " нет удалённой ветки"
    if not NAME.fullmatch(remote) or not NAME.fullmatch(rbranch):
        return None, "необычное имя источника — проверка не запускается"
    return (remote, rbranch, tracked), ""


def compare(root, ref):
    """(ahead, behind): commits only here, commits only on the source."""
    ahead, behind = git(root, "rev-list", "--left-right", "--count", "HEAD..." + ref).split()
    return int(ahead), int(behind)


def names(raw):
    """A -z list from git as file names: split on NUL only, each name decoded as the file system does."""
    return [os.fsdecode(b) for b in raw.split(b"\0") if b]


def shown(name):
    """A file name for the window: bytes that are not UTF-8 are shown as �."""
    return os.fsencode(name).decode("utf-8", "replace")


def incoming_over_files(root, ref):
    """The user's own files (untracked: data) that the update would replace: a path it adds (new or renamed
    into) that already exists here, and any leading part of an added path that is here a file or a link,
    not a real folder, and not a file of the program (git would put the new folder in its place).
    git would do both silently, so the update must not run."""
    added = names(git_raw(root, "diff", "--name-only", "-z", "--no-renames", "--diff-filter=A", "HEAD", ref))
    tracked = set(names(git_raw(root, "ls-files", "-z")))
    over = []
    for p in added:
        parts = p.split("/")
        for i in range(1, len(parts)):
            q = "/".join(parts[:i])
            full = root / q
            if q not in tracked and (os.path.islink(full) or (os.path.lexists(full) and not os.path.isdir(full))):
                over.append(q)
                break
        else:
            if os.path.lexists(root / p):
                over.append(p)
    return list(dict.fromkeys(over))


def local_changes(root):
    """Tracked files of the program changed here, as names (untracked and ignored files — data — do not count)."""
    raw, found, i = git_raw(root, "status", "--porcelain", "-z", "--untracked-files=no").split(b"\0"), [], 0
    while i < len(raw):
        entry, i = raw[i], i + 1
        if len(entry) > 3:
            found.append(os.fsdecode(entry[3:]))
            if entry[:1] in (b"R", b"C") or entry[1:2] in (b"R", b"C"):
                i += 1                      # a rename or a copy: its old name follows
    return found


def blocked_by_git(lines):
    """The files git names when it refuses a merge (each on its own line, after a tab)."""
    return [line[1:] for line in lines if line.startswith("\t") and line[1:].strip()]


def set_state(**values):
    _STATE.update(values)
    _STAMP[0] += 1
    _STATE["version"] = _STAMP[0]


def check(root=None, fetch=True):
    """One check: fetch, then compare. Returns the new state (a copy). Never raises."""
    root = root or HERE
    with _LOCK:
        set_state(state="checking", error="")
        try:
            source, why = update_source(root)
            if source is None:
                set_state(state="unavailable", behind=0, ahead=0, source="", error=why, checked=now_text())
                return dict(_STATE)
            remote, branch, ref = source
            if fetch:
                git(root, "fetch", "--quiet", "--no-tags", remote, branch, timeout=FETCH_TIMEOUT)
            ahead, behind = compare(root, ref)
            state = "current" if not ahead and not behind else "available" if not ahead else "ahead" if not behind else "diverged"
            set_state(state=state, behind=behind, ahead=ahead, source=ref, error="", checked=now_text())
        except UpdateError as exc:
            set_state(state="error", error=str(exc), checked=now_text())
        except Exception as exc:     # the program goes on whatever happens here
            set_state(state="error", error=f"{type(exc).__name__}: {exc}", checked=now_text())
        return dict(_STATE)


def apply(root=None):
    """The button «Обновить»: check again, then a fast-forward only. Returns a result for the window."""
    root = root or HERE
    result = check(root)
    if result["state"] != "available":
        return {"ok": False, "error": "обновлять нечего" if result["state"] == "current" else
                "обновление невозможно: " + (result["error"] or result["state"]), "updates": result}
    over_text = "обновление принесло бы файлы на место ваших файлов, они были бы потеряны — обновление не запускалось"
    with _LOCK:
        try:
            changed = local_changes(root)
            if changed:
                return {"ok": False, "code": "local-changes", "error": "в файлах программы есть свои правки — обновление не запускалось",
                        "files": [shown(n) for n in changed[:20]], "updates": dict(_STATE)}
            over = incoming_over_files(root, _STATE["source"])
            if over:
                return {"ok": False, "code": "incoming-over-files", "error": over_text,
                        "files": [shown(n) for n in over[:20]], "updates": dict(_STATE)}
            before = git(root, "rev-parse", "HEAD")
            try:
                # --no-overwrite-ignore: if a file of the user's is still in the way, git refuses instead of replacing it
                git(root, "merge", "--ff-only", "--no-overwrite-ignore", "--quiet", _STATE["source"], timeout=FETCH_TIMEOUT)
            except UpdateError as exc:
                blocked = blocked_by_git(exc.lines)
                if not blocked:
                    raise
                return {"ok": False, "code": "incoming-over-files", "error": over_text, "files": blocked[:20],
                        "updates": dict(_STATE)}
            after = git(root, "rev-parse", "HEAD")
        except UpdateError as exc:
            set_state(state="error", error=str(exc), checked=now_text())
            return {"ok": False, "error": str(exc), "updates": dict(_STATE)}
        set_state(state="updated", behind=0, ahead=0, error="", checked=now_text(), restart=True)
        return {"ok": True, "before": before[:7], "after": after[:7], "restart": True, "updates": dict(_STATE)}


def enabled():
    return read_settings().get("updates") == "on"


def view():
    """For data.js: the setting and the last state. While the setting is off, nothing is checked."""
    on = enabled()
    state = dict(_STATE) if on or _STATE["restart"] else dict(_STATE, state="off")
    state.pop("version", None)
    return dict(state, enabled=on)


def stamp():
    return _STAMP[0]


def check_in_background():
    """At start and at sync: one check in a thread, if the setting is on and no check is running.
    When it ends, data.js is rebuilt so the window sees the result."""
    if not enabled() or _LOCK.locked():
        return False

    def run():
        check()
        with SYNC_LOCK:
            build()
            LAST_STAMPS[0] = stamps()
    threading.Thread(target=run, daemon=True).start()
    return True


def update_check_now():
    """POST /update/check: the button «Проверить сейчас» (works only with the setting on)."""
    if not enabled():
        return {"ok": False, "error": "проверка обновлений выключена в настройках"}
    result = check()
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()
    return {"ok": result["state"] not in ("error", "unavailable"), "updates": view(), "error": result["error"]}


def update_apply():
    """POST /update/apply: the button «Обновить»."""
    if not enabled():
        return {"ok": False, "error": "проверка обновлений выключена в настройках"}
    result = apply()
    with SYNC_LOCK:
        build()
        LAST_STAMPS[0] = stamps()
    result["updates"] = view()
    return result


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .settings import (read_settings)  # noqa: E402
from .build import (LAST_STAMPS, SYNC_LOCK, build, stamps)  # noqa: E402
