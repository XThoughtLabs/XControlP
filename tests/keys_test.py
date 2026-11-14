# -*- coding: utf-8 -*-
"""Checks of the optional projects.json keys digest_topics and icons on the program's side (Python 3.10+,
standard library only).

    python -B tests/keys_test.py        exit 0: every check passes; exit 1: a check failed

Each check tries to break one rule. Nothing is written outside a temporary folder; no git command and no
network call runs (the digest store reads only a temporary folder; its git calls are replaced in T6).
"""
import datetime
import json
import os
import pathlib
import re
import shutil
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


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def main():
    os.environ.pop("PULT_DIGEST_REPO", None)       # the variable would win over digest_repo in projects.json
    import digest_store
    import pult.digests as glue
    from pult.settings import ICON_PATH

    # T1: a topic id is checked whole (a trailing newline is not a valid id), within its length; labels 1 to 80;
    # a built-in id is not replaced.
    got = digest_store.extra_topics({
        "robotics": "Robotics", "news\n": "News", "a" * 41: "Long", "b" * 42: "Too long", "llm-models": "Mine",
        "Upper": "X", "-dash": "X", "label80": "x" * 80, "label81": "x" * 81, "blank": "  ", "number": 5})
    check("T1 digest topic ids checked whole, labels 1 to 80, built-in ids kept",
          got == {"robotics": "Robotics", "a" * 41: "Long", "label80": "x" * 80}, repr(got))

    folder = pathlib.Path(tempfile.mkdtemp(prefix="keys-test-"))
    try:
        source = folder / "projects.json"
        glue.SOURCE = source                       # read by digest_repo() and digest_topics() at every call
        repo_a, repo_b = folder / "digests-a", folder / "digests-b"

        # T2: a change of the topics keeps the store of the same repository: the same lock and the same push state.
        write(source, {"digest_repo": str(repo_a), "digest_topics": {"robotics": "Robotics"}})
        first = glue.digest_store()
        lock, push = first.lock, first.last_push
        write(source, {"digest_repo": str(repo_a), "digest_topics": {"robotics": "Robots"}})
        second = glue.digest_store()
        kept = second is first and second.lock is lock and second.last_push is push and second.topics.get("robotics") == "Robots"

        # While a push holds the store's lock, a topic change must not hand out a lock another thread can take.
        held, release = threading.Event(), threading.Event()

        def slow_push():
            with first.lock:
                held.set()
                release.wait(5)

        worker = threading.Thread(target=slow_push)
        worker.start()
        held.wait(5)
        write(source, {"digest_repo": str(repo_a), "digest_topics": {"robotics": "Robotics 2"}})
        third = glue.digest_store()
        taken = third.lock.acquire(timeout=0.2)
        if taken:
            third.lock.release()
        release.set()
        worker.join(5)
        check("T2 topic change keeps the store, its lock and its push state",
              kept and third is first and not taken and third.topics.get("robotics") == "Robotics 2",
              f"same store: {second is first}/{third is first}, same lock: {second.lock is lock}, "
              f"lock taken during a push: {taken}, topics: {third.topics.get('robotics')!r}")

        # T3: another repository gets its own store.
        write(source, {"digest_repo": str(repo_b), "digest_topics": {"robotics": "Robotics 2"}})
        fourth = glue.digest_store()
        check("T3 another repository - a new store", fourth is not first and fourth.repo == pathlib.Path(str(repo_b)),
              f"same store: {fourth is first}, repo: {fourth.repo}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    # T4: an image name is at most 40 characters on both sides: the server's ICON_PATH and the window's ICON_NAME_RE.
    n40, n41 = "a" * 40, "a" * 41
    server = [bool(ICON_PATH.match(f"/icons/comic/{n}.png")) for n in (n40, n41)]
    found = re.search(r"const ICON_NAME_RE = /(.+?)/;", (ROOT / "js" / "01-core.js").read_text(encoding="utf-8"))
    window = [bool(re.search(found.group(1), n)) for n in (n40, n41)] if found else None
    check("T4 image name: 40 characters taken, 41 refused, by the server and by the window",
          server == [True, False] and window == [True, False], f"server {server}, window {window}")

    # T5: set_topics() replaces the topics dict and never changes it in place, so a view that already holds
    # the old dict keeps one consistent set (the reason set_topics() needs no lock).
    store = digest_store.Digests(None, {"robotics": "Robotics"})
    old = store.topics
    store.set_topics({"robotics": "Robots"})
    check("T5 set_topics() replaces the topics, the old dict stays as it was",
          store.topics is not old and old.get("robotics") == "Robotics" and store.topics.get("robotics") == "Robots",
          f"same dict: {store.topics is old}, old: {old.get('robotics')!r}, new: {store.topics.get('robotics')!r}")

    # T6: view() reads the topics once, so one data.js never mixes two topic sets.
    class Counting(digest_store.Digests):
        reads = 0

        @property
        def topics(self):
            type(self).reads += 1
            return self._topics

        @topics.setter
        def topics(self, value):
            self._topics = value

    def no_git(*args, **kwargs):
        raise digest_store.DigestError("no git in this test")

    folder = pathlib.Path(tempfile.mkdtemp(prefix="keys-test-"))
    try:
        (folder / ".git").mkdir()
        today = datetime.date.today()
        day_file = folder / "digests" / f"{today:%Y}" / f"{today:%m}" / f"{today:%Y-%m-%d}.json"
        day_file.parent.mkdir(parents=True)
        day_file.write_text(json.dumps({"items": [{"title": f"item {n}", "topic": "robotics"} for n in range(3)]}),
                            encoding="utf-8")
        counting = Counting(str(folder), {"robotics": "Robotics"})
        counting.git = no_git
        Counting.reads = 0
        shown = counting.view()
        items = [it for d in shown.get("digests", []) for it in d.get("items", [])]
        check("T6 view() reads the topics once per view",
              Counting.reads == 1 and len(items) == 3 and all(it["topic"] == "robotics" for it in items),
              f"reads: {Counting.reads}, items: {len(items)}, ok: {shown.get('ok')}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    print(f"\nPassed {len(PASSED)}, failed {len(FAILED)}" + (": " + ", ".join(FAILED) if FAILED else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
