# -*- coding: utf-8 -*-
"""Checks of the update check (pult/updates.py) on temporary local repositories (Python 3.10+, standard
library only; git must be installed).

    python -B tests/update_test.py        exit 0: every check passes; exit 1: a check failed

Each check tries to break one rule: the program updates only on a click, only as a fast-forward, only
without local changes to tracked files, never touches data files, and stays calm when the folder is not
a clone, git is missing or the network does not answer. Nothing is written outside a temporary folder;
no network call runs (the "remote" is a bare repository in the temporary folder).
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  - {detail}"))


ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@example.com", GIT_TERMINAL_PROMPT="0")


def sh(cwd, *args):
    done = subprocess.run(["git", "-C", str(cwd)] + list(args), capture_output=True, env=ENV)
    if done.returncode != 0:
        raise RuntimeError(f"git {args}: {done.stderr.decode('utf-8', 'replace')}")
    return done.stdout.decode("utf-8", "replace").strip()


def commit(work, name, text):
    (work / name).write_text(text, encoding="utf-8")
    sh(work, "add", name)
    sh(work, "commit", "-q", "-m", "change " + name)
    return sh(work, "rev-parse", "HEAD")


def world(base, name, branch="modules"):
    """A bare 'GitHub' repository, a writer clone that publishes, and the program's clone (the Pult)."""
    remote, writer, program = base / (name + ".git"), base / (name + "-writer"), base / (name + "-pult")
    sh(base, "init", "-q", "--bare", "-b", branch, str(remote))
    sh(base, "clone", "-q", str(remote), str(writer))
    sh(writer, "checkout", "-q", "-b", branch)
    (writer / ".gitignore").write_text("data.js\nsettings.json\nreports/\nnotes\nlinks\n*.dat\n", encoding="utf-8")
    sh(writer, "add", ".gitignore")
    commit(writer, "app.py", "v1\n")
    sh(writer, "push", "-q", "origin", branch)
    sh(base, "clone", "-q", "-b", branch, str(remote), str(program))
    (program / "data.js").write_text("my data\n", encoding="utf-8")          # data: ignored by git
    (program / "settings.json").write_text('{"updates": "on"}\n', encoding="utf-8")
    return remote, writer, program


def force(writer, rel, text, message, branch="modules"):
    """The source commits a file at a path that is ignored in the program's folder (git add -f) and publishes it."""
    path = writer / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    sh(writer, "add", "-f", "--", rel)
    sh(writer, "commit", "-q", "-m", message)
    sh(writer, "push", "-q", "origin", branch)


def link(target, path):
    """A symbolic link, or False where the system does not allow it (Windows without the right)."""
    try:
        os.symlink(str(target), str(path))
        return True
    except (OSError, NotImplementedError):
        return False


def publish(writer, name, text, branch="modules"):
    head = commit(writer, name, text)
    sh(writer, "push", "-q", "origin", branch)
    return head


def main():
    if not shutil.which("git"):
        print("FAIL git is not installed: the update check needs git")
        return 1
    import pult.updates as up
    import pult.settings as settings

    base = pathlib.Path(tempfile.mkdtemp(prefix="update-test-"))
    try:
        # U1: a clone equal to its source is current; the source is the branch's own upstream.
        remote, writer, program = world(base, "u1")
        r = up.check(program)
        check("U1 equal clone: current, source origin/modules", r["state"] == "current" and r["source"] == "origin/modules"
              and r["behind"] == 0 and r["ahead"] == 0, repr(r))

        # U2: two new commits on the source: available, behind 2; the check itself changes no file of the program.
        publish(writer, "app.py", "v2\n")
        new = publish(writer, "more.py", "x\n")
        head_before = sh(program, "rev-parse", "HEAD")
        r = up.check(program)
        check("U2 newer source: available, behind 2, HEAD unchanged by the check",
              r["state"] == "available" and r["behind"] == 2 and sh(program, "rev-parse", "HEAD") == head_before
              and (program / "app.py").read_text(encoding="utf-8") == "v1\n", repr(r))

        # U3: a tracked file changed locally: no update, the file and HEAD stay as they are.
        (program / "app.py").write_text("my edit\n", encoding="utf-8")
        r = up.apply(program)
        check("U3 local change to a tracked file: refused, file and HEAD kept",
              not r["ok"] and "правки" in r["error"] and (program / "app.py").read_text(encoding="utf-8") == "my edit\n"
              and sh(program, "rev-parse", "HEAD") == head_before, repr(r))
        check("U3b the refusal has its code and names the changed file whole",
              r.get("code") == "local-changes" and r.get("files") == ["app.py"], repr(r))
        sh(program, "checkout", "-q", "--", "app.py")

        # U4: the update: a fast-forward to the source; data files (ignored) untouched; restart asked.
        r = up.apply(program)
        check("U4 update: fast-forward to the source, data untouched, restart asked",
              r["ok"] and r.get("restart") is True and sh(program, "rev-parse", "HEAD") == new
              and (program / "app.py").read_text(encoding="utf-8") == "v2\n"
              and (program / "data.js").read_text(encoding="utf-8") == "my data\n"
              and (program / "settings.json").read_text(encoding="utf-8") == '{"updates": "on"}\n'
              and up.view()["restart"] is True, repr(r))

        # U5: local commits only: ahead, the button refuses, nothing changes.
        remote, writer, program = world(base, "u5")
        mine = commit(program, "local.py", "mine\n")
        r = up.apply(program)
        check("U5 own commits only: ahead, update refused, HEAD kept",
              r["updates"]["state"] == "ahead" and not r["ok"] and sh(program, "rev-parse", "HEAD") == mine, repr(r))

        # U6: own commits and new commits on the source: diverged, refused, no merge commit made.
        publish(writer, "app.py", "v2\n")
        r = up.apply(program)
        check("U6 diverged: refused, no merge, HEAD kept",
              r["updates"]["state"] == "diverged" and not r["ok"] and sh(program, "rev-parse", "HEAD") == mine
              and sh(program, "rev-list", "--count", "HEAD") == "2", repr(r))

        # U7: a fork with a remote «upstream»: the original is checked, not the fork.
        remote, writer, program = world(base, "u7")
        original, owriter, _ = world(base, "u7orig")
        sh(program, "remote", "add", "upstream", str(original))
        sh(program, "fetch", "-q", "upstream")
        sh(program, "reset", "-q", "--hard", "upstream/modules")
        publish(owriter, "fix.py", "fix\n")
        r = up.check(program)
        check("U7 fork: source upstream/modules, its new commit found", r["source"] == "upstream/modules"
              and r["state"] == "available" and r["behind"] == 1, repr(r))

        # U8: a folder that is not a git clone: unavailable, no exception, no change.
        plain = base / "plain"
        plain.mkdir()
        (plain / "data.js").write_text("x\n", encoding="utf-8")
        r = up.check(plain)
        check("U8 not a clone: unavailable, calm", r["state"] == "unavailable" and "не клон" in r["error"], repr(r))

        # U9: no git on the computer: unavailable, no exception.
        real = up.git_exe
        up.git_exe = lambda: None
        try:
            remote, writer, program = world(base, "u9")
            r = up.check(program)
        finally:
            up.git_exe = real
        check("U9 no git: unavailable, calm", r["state"] == "unavailable" and "git не найден" in r["error"], repr(r))

        # U10: the source cannot be reached: error with the reason, no exception, HEAD kept.
        remote, writer, program = world(base, "u10")
        sh(program, "remote", "set-url", "origin", str(base / "nowhere.git"))
        head = sh(program, "rev-parse", "HEAD")
        r = up.check(program)
        check("U10 source unreachable: error with a reason, HEAD kept",
              r["state"] == "error" and r["error"] and sh(program, "rev-parse", "HEAD") == head, repr(r))

        # U11: the network does not answer: the fetch is cut after its time limit, the state says so.
        # (A stand-in git that sleeps on fetch needs a POSIX shell: on Windows the check is reported as skipped.)
        slow = base / "slow-git"
        slow.mkdir()
        fake = slow / "git"
        fake.write_text("#!/bin/sh\nfor a in \"$@\"; do if [ \"$a\" = fetch ]; then sleep 5; fi; done\nexec %s \"$@\"\n"
                        % shutil.which("git"), encoding="utf-8")
        fake.chmod(0o755)
        limit, real = up.FETCH_TIMEOUT, up.git_exe
        if os.name != "nt":
            up.FETCH_TIMEOUT, up.git_exe = 1, (lambda: str(fake))
        if os.name == "nt":
            print("skip U11 silent network (needs a POSIX shell for the stand-in git; runs on Linux in CI)")
        else:
            try:
                remote, writer, program = world(base, "u11")
                r = up.check(program)
            finally:
                up.FETCH_TIMEOUT, up.git_exe = limit, real
            check("U11 silent network: cut after the time limit, error says so",
                  r["state"] == "error" and "не ответил" in r["error"], repr(r))

        # U15: the source commits a file at the path of the user's ignored data file (data.js is in .gitignore, so git
        # itself would overwrite it silently): the update is refused and names it; the file and HEAD are kept.
        remote, writer, program = world(base, "u15")
        (writer / "data.js").write_text("example\n", encoding="utf-8")
        sh(writer, "add", "-f", "data.js")
        sh(writer, "commit", "-q", "-m", "an example data file")
        sh(writer, "push", "-q", "origin", "modules")
        head = sh(program, "rev-parse", "HEAD")
        r = up.apply(program)
        check("U15 the update would overwrite an ignored data file: refused, named, file and HEAD kept",
              not r["ok"] and "data.js" in r.get("files", []) and sh(program, "rev-parse", "HEAD") == head
              and (program / "data.js").read_text(encoding="utf-8") == "my data\n", repr(r))

        # XCP-27: the user's own files that the update would replace are found whatever the shape of the change
        # (each check also asks incoming_over_files directly, so git's own refusal cannot hide a gap in it).
        def refused(r, program, name):
            return (not r["ok"] and r.get("code") == "incoming-over-files" and name in r.get("files", [])
                    and r["updates"]["state"] == "available")

        # U26: the program's own list refuses before git is asked to merge (git's refusal is only the second guard).
        remote, writer, program = world(base, "u26")
        force(writer, "data.js", "example\n", "an example data file")
        calls = []
        real_run = up.subprocess.run
        up.subprocess.run = lambda *a, **k: calls.append(list(a[0])) or real_run(*a, **k)
        try:
            r = up.apply(program)
        finally:
            up.subprocess.run = real_run
        check("U26 the refusal comes from the program's own list: no merge is run", refused(r, program, "data.js")
              and calls and not any("merge" in c for c in calls), repr((r, [c[3:5] for c in calls])))

        # U18: the source renames a program file into the path of the user's ignored data file.
        remote, writer, program = world(base, "u18")
        publish(writer, "tmpl.txt", "template\n")
        sh(program, "pull", "-q", "--ff-only")
        sh(writer, "mv", "-f", "tmpl.txt", "data.js")
        sh(writer, "commit", "-q", "-m", "rename into data.js")
        sh(writer, "push", "-q", "origin", "modules")
        up.check(program)
        named = up.incoming_over_files(program, "origin/modules")
        r = up.apply(program)
        check("U18 a rename into an ignored data path: found, refused, file kept", named == ["data.js"] and refused(r, program, "data.js")
              and (program / "data.js").read_text(encoding="utf-8") == "my data\n", repr((named, r)))

        # U19: the source adds a file inside the user's ignored folder (reports/ is ignored, reports/r.md is the user's).
        remote, writer, program = world(base, "u19")
        (program / "reports").mkdir()
        (program / "reports" / "r.md").write_text("my report\n", encoding="utf-8")
        force(writer, "reports/r.md", "example report\n", "an example report")
        up.check(program)
        named = up.incoming_over_files(program, "origin/modules")
        r = up.apply(program)
        check("U19 a file inside an ignored folder: found, refused, file kept", named == ["reports/r.md"] and refused(r, program, "reports/r.md")
              and (program / "reports" / "r.md").read_text(encoding="utf-8") == "my report\n", repr((named, r)))

        # U20: the user's ignored link that points nowhere sits at the path the source adds.
        remote, writer, program = world(base, "u20")
        if not link(base / "nowhere-target", program / "links"):
            print("skip U20 dangling link (this system does not allow symbolic links here)")
        else:
            force(writer, "links", "a file\n", "a file named links")
            up.check(program)
            named = up.incoming_over_files(program, "origin/modules")
            r = up.apply(program)
            check("U20 a dangling ignored link at an incoming path: found, refused, link kept", named == ["links"]
                  and refused(r, program, "links") and os.path.islink(program / "links"), repr((named, r)))

        # U21 (G1): the source adds notes/readme.md where «notes» is the user's ignored FILE: git would delete the file
        # and make a folder.
        remote, writer, program = world(base, "u21")
        (program / "notes").write_text("my notes\n", encoding="utf-8")
        force(writer, "notes/readme.md", "readme\n", "a notes folder")
        head = sh(program, "rev-parse", "HEAD")
        up.check(program)
        named = up.incoming_over_files(program, "origin/modules")
        r = up.apply(program)
        check("U21 a folder over the user's ignored file: found, refused, file and HEAD kept", named == ["notes"]
              and refused(r, program, "notes") and (program / "notes").read_text(encoding="utf-8") == "my notes\n"
              and sh(program, "rev-parse", "HEAD") == head, repr((named, r)))

        # U23: if the program's own list misses such a file, git itself refuses (--no-overwrite-ignore) and names it;
        # the state stays «available», nothing is replaced.
        real_over = up.incoming_over_files
        up.incoming_over_files = lambda root, ref: []
        try:
            r = up.apply(program)
        finally:
            up.incoming_over_files = real_over
        check("U23 git's own refusal (--no-overwrite-ignore): refused, named, file and HEAD kept", refused(r, program, "notes")
              and (program / "notes").read_text(encoding="utf-8") == "my notes\n" and sh(program, "rev-parse", "HEAD") == head, repr(r))

        # U22 (G1): the user's ignored link «links» points to a folder elsewhere; the source adds links/new.md.
        remote, writer, program = world(base, "u22")
        outside = base / "u22-outside"
        outside.mkdir()
        if not link(outside, program / "links"):
            print("skip U22 linked folder (this system does not allow symbolic links here)")
        else:
            force(writer, "links/new.md", "new\n", "a links folder")
            up.check(program)
            named = up.incoming_over_files(program, "origin/modules")
            r = up.apply(program)
            check("U22 a folder over the user's ignored link: found, refused, link kept", named == ["links"]
                  and refused(r, program, "links") and os.path.islink(program / "links"), repr((named, r)))

        # U24 (G2): names are read as they are on disk: a leading space is kept; a name that is not UTF-8 is found
        # (POSIX systems other than macOS only: Windows and macOS cannot hold such a name).
        remote, writer, program = world(base, "u24")
        (program / " my.dat").write_text("mine\n", encoding="utf-8")
        odd = os.fsdecode(b"d\xe9.dat") if os.name != "nt" and sys.platform != "darwin" else None
        if odd:
            (program / odd).write_text("mine too\n", encoding="utf-8")
            force(writer, odd, "{}\n", "an odd name")
        else:
            print("skip U24 part: a name that is not UTF-8 (this system cannot hold one)")
        force(writer, " my.dat", "{}\n", "a name with a leading space")
        up.check(program)
        named = up.incoming_over_files(program, "origin/modules")
        r = up.apply(program)
        want = sorted([" my.dat"] + ([odd] if odd else []))
        check("U24 a leading space and a name that is not UTF-8: found, refused, files kept", sorted(named) == want
              and refused(r, program, " my.dat") and (not odd or "d\ufffd.dat" in r.get("files", []))
              and (program / " my.dat").read_text(encoding="utf-8") == "mine\n", repr((named, r)))

        # U25: a file of the program that the source turns into a folder is not the user's file: the update runs.
        remote, writer, program = world(base, "u25")
        publish(writer, "tool", "one file\n")
        sh(program, "pull", "-q", "--ff-only")
        sh(writer, "rm", "-q", "tool")
        (writer / "tool").mkdir()
        (writer / "tool" / "main.py").write_text("now a folder\n", encoding="utf-8")
        sh(writer, "add", "tool/main.py")
        sh(writer, "commit", "-q", "-m", "tool becomes a folder")
        sh(writer, "push", "-q", "origin", "modules")
        r = up.apply(program)
        check("U25 a program file that becomes a folder: not refused, the update runs", r["ok"]
              and (program / "tool" / "main.py").read_text(encoding="utf-8") == "now a folder\n"
              and (program / "data.js").read_text(encoding="utf-8") == "my data\n", repr(r))

        # XCP-28: git's refusal is read by the kind of message; a program folder is the program's; every answer has a code.
        # U27 (H1): a local edit git sees but `git status` hides (skip-worktree): git refuses with "Your local changes";
        # that is the refusal «own edits in the program's files», never «your files are in the way».
        remote, writer, program = world(base, "u27")
        publish(writer, "app.py", "v2\n")
        sh(program, "update-index", "--skip-worktree", "app.py")
        (program / "app.py").write_text("my edit\n", encoding="utf-8")
        head = sh(program, "rev-parse", "HEAD")
        r = up.apply(program)
        check("U27 a hidden local edit of a program file: refused as local changes, file and HEAD kept",
              not r["ok"] and r.get("code") == "local-changes" and r.get("files") == ["app.py"] and r["updates"]["state"] == "available"
              and (program / "app.py").read_text(encoding="utf-8") == "my edit\n" and sh(program, "rev-parse", "HEAD") == head, repr(r))

        # U28 (H2): a program folder holding only program files, which the source turns into a file: the update runs;
        # the same folder holding a user's ignored file: refused, the folder named, the file kept.
        remote, writer, program = world(base, "u28")
        (writer / "lib").mkdir()
        publish(writer, "lib/a.py", "a\n")
        sh(program, "pull", "-q", "--ff-only")
        sh(writer, "rm", "-q", "-r", "lib")
        publish(writer, "lib", "now a file\n")
        r = up.apply(program)
        check("U28 a program folder that becomes a file: not refused, the update runs", r["ok"]
              and (program / "lib").read_text(encoding="utf-8") == "now a file\n", repr(r))
        remote, writer, program = world(base, "u28b")
        (writer / "lib").mkdir()
        publish(writer, "lib/a.py", "a\n")
        sh(program, "pull", "-q", "--ff-only")
        (program / "lib" / "mine.dat").write_text("mine\n", encoding="utf-8")
        sh(writer, "rm", "-q", "-r", "lib")
        publish(writer, "lib", "now a file\n")
        up.check(program)
        named = up.incoming_over_files(program, "origin/modules")
        r = up.apply(program)
        check("U28b the same folder holding a user's ignored file: found, refused, folder named, file kept", named == ["lib"] and refused(r, program, "lib")
              and (program / "lib" / "mine.dat").read_text(encoding="utf-8") == "mine\n", repr((named, r)))

        # U3c (H3): the changed program files are named whole, also for a rename whose old name starts with R.
        remote, writer, program = world(base, "u3c")
        publish(writer, "README.md", "readme\n")
        sh(program, "pull", "-q", "--ff-only")
        publish(writer, "more.py", "x\n")
        sh(program, "mv", "README.md", "docs.md")
        (program / "app.py").write_text("my edit\n", encoding="utf-8")
        r = up.apply(program)
        check("U3c local changes with a rename: exactly the new name and the edited file", not r["ok"] and r.get("code") == "local-changes"
              and sorted(r.get("files", [])) == ["app.py", "docs.md"], repr(r))

        # U29 (H6): the button's other answers carry a code and the state: nothing to update, own commits only.
        remote, writer, program = world(base, "u29")
        current = up.apply(program)
        commit(program, "local.py", "mine\n")
        ahead = up.apply(program)
        check("U29 nothing to update and own commits: refused with code «state» and the state", not current["ok"]
              and current.get("code") == "state" and current.get("state") == "current" and not ahead["ok"]
              and ahead.get("code") == "state" and ahead.get("state") == "ahead", repr((current, ahead)))

        # U30 (H6): a merge that git refuses for another reason: code «update-failed», git's own line kept as data.
        remote, writer, program = world(base, "u30")
        publish(writer, "app.py", "v2\n")
        real_git = up.git

        def failing(root, *args, **kw):
            if args and args[0] == "merge":
                raise up.UpdateError("fatal: something else", ["fatal: something else"])
            return real_git(root, *args, **kw)
        up.git = failing
        try:
            r = up.apply(program)
        finally:
            up.git = real_git
        check("U30 another refusal of the merge: code update-failed, git's line as detail, state error", not r["ok"]
              and r.get("code") == "update-failed" and r.get("detail") == "fatal: something else" and r["updates"]["state"] == "error", repr(r))

        # U17: an option-like branch name never reaches git fetch: the check refuses to run.
        remote, writer, program = world(base, "u17")
        sh(program, "update-ref", "refs/heads/--upload-pack=touch", "HEAD")
        sh(program, "symbolic-ref", "HEAD", "refs/heads/--upload-pack=touch")
        r = up.check(program)
        check("U17 an option-like branch name: unavailable, nothing run", r["state"] == "unavailable" and "имя" in r["error"]
              and not (program / "touch").exists(), repr(r))

        # U16: a background check is not started while another check holds the lock.
        real_settings = up.read_settings
        up.read_settings = lambda: {"updates": "on"}
        try:
            with up._LOCK:
                busy = up.check_in_background()
        finally:
            up.read_settings = real_settings
        check("U16 no second background check while one runs", busy is False, repr(busy))

        # U12: with the setting off, no git command runs at all (start, sync, both buttons).
        calls = []
        real_run = up.subprocess.run
        up.subprocess.run = lambda *a, **k: calls.append(a) or real_run(*a, **k)
        real_settings = up.read_settings
        up.read_settings = lambda: {"updates": "off"}
        up._STATE["restart"] = False                  # no update in this run: the window must see «off»
        try:
            started = up.check_in_background()
            now = up.update_check_now()
            applied = up.update_apply()
            shown = up.view()
        finally:
            up.subprocess.run = real_run
            up.read_settings = real_settings
        check("U12 setting off: no git command, buttons refuse, the window sees off",
              not calls and started is False and not now["ok"] and not applied["ok"] and shown["enabled"] is False
              and shown["state"] == "off" and "выключена" in now["error"] and "выключена" in applied["error"]
              and now.get("code") == applied.get("code") == "state" and now.get("state") == applied.get("state") == "off", repr((calls, shown, now, applied)))

        # U13: a detached HEAD (not on a branch): unavailable.
        remote, writer, program = world(base, "u13")
        sh(program, "checkout", "-q", "--detach")
        r = up.check(program)
        check("U13 detached HEAD: unavailable", r["state"] == "unavailable" and "ветке" in r["error"], repr(r))

        # U14: the setting is one of off|on, off by default; a foreign value is refused.
        folder = base / "settings"
        folder.mkdir()
        settings.SETTINGS = folder / "settings.json"
        default = settings.read_settings()["updates"]
        settings.SETTINGS.write_text(json.dumps({"updates": "yes"}), encoding="utf-8")
        foreign = settings.read_settings()["updates"]
        refused = settings.setting_choices()["updates"]
        check("U14 setting: off by default, only off|on", default == "off" and foreign == "off" and refused == ("off", "on"),
              repr((default, foreign, refused)))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
