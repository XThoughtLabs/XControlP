# -*- coding: utf-8 -*-
"""Oracle for XControlP: freezes what the program produces, so that a change of structure can be proved
to change nothing. Standard library only, Python 3.10+.

    python -B tests/oracle/run_oracle.py check [--out DIR]
        Run the program of this repository on tests/oracle/sample.json and compare with tests/oracle/expected.
        With --out (a new or empty folder), the outputs and the full list of differences (diff.txt) stay there.
    python -B tests/oracle/run_oracle.py freeze
        Write tests/oracle/expected from the program of this repository. Only when a change of behaviour
        is intended and the owner has said so.
    python -B tests/oracle/run_oracle.py compare --old DIR --new DIR --data DIR [--out DIR]
        Run two copies of the program on the same data and compare. For real data: the outputs stay in
        --out (outside any repository) or in a temporary folder. With --out, the full list of differences
        is written to DIR/diff.txt.

Each run happens in a fresh subprocess, in a temporary copy: the data folder first, then the program files
over it. Nothing is written into the program, the data or the repository (except "freeze"). The run fixes:
- today = 2026-01-15, now = 2026-01-15 10:00:00 at UTC+02:00 (datetime.date / datetime.datetime are replaced
  on the datetime module before the program is loaded; naive times are taken to be in that zone);
- uuid.uuid4 = a counter (00000000000000000000000000000001, …);
- the modification time of every copied file = that moment;
- PYTHONHASHSEED=0, PYTHONUTF8=1, PULT_DIGEST_REPO empty.
Outputs are normalised: the temporary folder becomes <ROOT>, the server's key <TOKEN>, its port <PORT>;
line ends CR LF become LF and the SQLite library's version becomes <SQLITE> (both differ by machine, not by
program); Python's own error page (send_error) is recorded by status and type only, because its text differs
by Python version. Text answers and text files are measured and hashed after this normalisation.

What it records: data.js after the first build; every answer of a fixed list of requests (pages, files,
icons, day plan, day results, refusals of the guards, and a few safe changes: language, alert marks, idea
flag, service removal, proposal mark, a request to HQ, day-plan operations); data.js after those changes; the
SHA-256 of every data file left in the copy. Synchronisation, Google sign-in, digest marks and «show in
folder» are never called: they use the network or open windows.

Contract with the program: the entry file XControlP.pyw exposes build() and the server class Pult
(attributes .token and .host, served with serve_forever). Exit codes: 0 pass, 1 differences, 2 usage or run error.
"""
import difflib
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
SAMPLE = HERE / "sample.json"      # the sample data as one file {"files": {relative path: text}}: the program's
                                    # data names (projects.json, ideas/, reports/ …) are ignored by .gitignore
EXPECTED = HERE / "expected"
OUTPUTS = ("data-js.txt", "responses.json", "data-after-js.txt", "files.json")
SKIP_TOP = {".git", ".github", "docs", "tests", "__pycache__", "README.md", "README.ru.md", "README.he.md",
            "LICENSE", "NOTICE", "AGENTS.md", "CLAUDE.md"}
TODAY, NOW, OFFSET_HOURS = (2026, 1, 15), (2026, 1, 15, 10, 0, 0), 2


# ---------------------------------------------------------------- helpers

def write_bytes(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def ignore_patterns(folder):
    try:
        lines = (folder / ".gitignore").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith(("#", "!"))]


def ignored(rel_parts, patterns, is_dir):
    for pattern in patterns:
        if pattern.endswith("/"):
            name = pattern.rstrip("/")
            folders = rel_parts if is_dir else rel_parts[:-1]
            if any(fnmatch.fnmatchcase(part, name) for part in folders):
                return True
        elif fnmatch.fnmatchcase(rel_parts[-1], pattern.lstrip("/")):
            return True
    return False


def copy_program(program, work):
    """The program's files over the data: everything except repository parts, docs and data files."""
    patterns = ignore_patterns(program)
    copied = []
    for path in sorted(program.rglob("*")):
        rel = path.relative_to(program)
        if rel.parts[0] in SKIP_TOP or "__pycache__" in rel.parts:
            continue
        if ignored(rel.parts, patterns, path.is_dir()):
            continue
        if path.is_file():
            target = work / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            copied.append(rel.as_posix())
    return copied


# ---------------------------------------------------------------- one run (inside a fresh subprocess)

def freeze_clock():
    import datetime as real
    import itertools
    import uuid

    zone = real.timezone(real.timedelta(hours=OFFSET_HOURS))
    base_date, base_datetime = real.date, real.datetime

    class FixedDate(base_date):
        @classmethod
        def today(cls):
            return cls(*TODAY)

    class FixedDateTime(base_datetime):
        @classmethod
        def now(cls, tz=None):
            moment = cls(*NOW)
            return moment if tz is None else base_datetime(*NOW, tzinfo=zone).astimezone(tz)

        @classmethod
        def today(cls):
            return cls(*NOW)

        @classmethod
        def utcnow(cls):
            return cls(*NOW) - real.timedelta(hours=OFFSET_HOURS)

        @classmethod
        def fromtimestamp(cls, t, tz=None):
            aware = base_datetime.fromtimestamp(t, zone)
            if tz is not None:
                return aware.astimezone(tz)
            return cls(aware.year, aware.month, aware.day, aware.hour, aware.minute, aware.second, aware.microsecond)

        def astimezone(self, tz=None):
            if self.tzinfo is None:
                aware = base_datetime(self.year, self.month, self.day, self.hour, self.minute, self.second,
                                      self.microsecond, tzinfo=zone)
            else:
                aware = base_datetime.astimezone(self, zone)
            return aware if tz is None else aware.astimezone(tz)

    real.date, real.datetime = FixedDate, FixedDateTime
    counter = itertools.count(1)
    uuid.uuid4 = lambda: uuid.UUID(int=next(counter))
    return base_datetime(*NOW, tzinfo=zone).timestamp()


def run_once(program, data, out):
    """Copy data then program into a temporary folder, run the program there, write the normalised outputs."""
    import http.client
    import importlib.machinery
    import importlib.util
    import threading

    stamp = freeze_clock()
    work = pathlib.Path(tempfile.mkdtemp(prefix="xcp-oracle-")).resolve()
    try:
        if data.is_dir():
            shutil.copytree(data, work, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        elif data.is_file():
            bundle = json.loads(data.read_text(encoding="utf-8"))
            for rel, text in sorted(bundle["files"].items()):
                target = work / rel
                if ".." in pathlib.PurePosixPath(rel).parts or work not in target.resolve().parents:
                    raise ValueError(f"bad path in the sample: {rel!r}")
                write_bytes(target, text.encode("utf-8"))
        program_files = set(copy_program(program, work))
        for path in work.rglob("*"):
            if path.is_file():
                os.utime(path, (stamp, stamp))

        sys.path.insert(0, str(work))
        loader = importlib.machinery.SourceFileLoader("xcp_entry", str(work / "XControlP.pyw"))
        spec = importlib.util.spec_from_loader("xcp_entry", loader)
        entry = importlib.util.module_from_spec(spec)
        sys.modules["xcp_entry"] = entry
        loader.exec_module(entry)

        roots = set()
        for form in (work, pathlib.Path(str(work))):
            for text in (str(form), form.as_posix(), form.as_uri()):
                roots.add(text)
                roots.add(json.dumps(text)[1:-1])
        secrets_seen = []

        def slashes(match):
            return "<ROOT>" + re.sub(r"\\\\|\\", "/", match.group(1))

        def normal(text):
            # line ends: the program writes its text files in text mode, so on Windows they end in CR LF
            text = text.replace("\r\n", "\n")
            for root in sorted(roots, key=len, reverse=True):
                text = text.replace(root, "<ROOT>")
            # a Windows path after the root ("<ROOT>\\ideas\\IDEAS.md" in JSON) reads like the Linux one
            text = re.sub(r'<ROOT>((?:(?:\\\\|\\)[^"\\<>\r\n]+)+)', slashes, text)
            for secret in secrets_seen:
                text = text.replace(secret, "<TOKEN>")
            # the SQLite library's version (day.json and the day plan's answers) differs by machine
            text = re.sub(r'("sqlite"\s*:\s*")\d+(?:\.\d+)+(")', r"\1<SQLITE>\2", text)
            return text

        if hasattr(entry, "first_start"):
            entry.first_start()
        entry.build()
        first_build = normal((work / "data.js").read_text(encoding="utf-8"))

        server = entry.Pult()
        secrets_seen.append(server.token)
        host = server.host
        port = int(host.rsplit(":", 1)[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def call(step, method, path, body=None, host_header=None, origin=True, token=True, kind="application/json",
                 length=None):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            conn.putheader("Host", host_header or host)
            if method == "POST":
                if origin:
                    conn.putheader("Origin", origin if isinstance(origin, str) else "http://" + host)
                if token:
                    conn.putheader("X-Pult-Token", token if isinstance(token, str) else server.token)
                payload = b"" if body is None else (body if isinstance(body, bytes) else
                                                    json.dumps(body, ensure_ascii=False).encode("utf-8"))
                if kind:
                    conn.putheader("Content-Type", kind)
                conn.putheader("Content-Length", str(len(payload) if length is None else length))
                conn.endheaders(payload if length is None else None)
            else:
                conn.endheaders()
            reply = conn.getresponse()
            raw = reply.read()
            conn.close()
            ctype = reply.getheader("Content-Type") or ""
            record = {"step": step, "method": method, "path": path, "status": reply.status, "type": ctype}
            if reply.status >= 400 and ctype.startswith("text/html") and b"<title>Error response</title>" in raw:
                # Python's own error page (send_error): its text differs by Python version, not by program
                record["body"] = "<PYTHON ERROR PAGE>"
                return record
            if ctype.startswith(("text/", "application/json")):
                text = normal(raw.decode("utf-8", errors="replace")).replace(f"127.0.0.1:{port}", "127.0.0.1:<PORT>")
                raw = text.encode("utf-8")
                if not path.startswith(("/data.js", "/i18n.js")) and len(text) <= 20000:
                    record["body"] = text
            record["bytes"] = len(raw)
            record["sha256"] = hashlib.sha256(raw).hexdigest()
            return record

        day = "2026-01-15"
        replies = [
            call("G01", "GET", "/"),
            call("G02", "GET", "/index.html"),
            call("G03", "GET", "/data.js"),
            call("G04", "GET", "/i18n.js"),
            call("G05", "GET", "/icon.svg"),
            call("G06", "GET", "/icon.ico"),
            call("G07", "GET", "/icons/comic/ideas.png"),
            call("G08", "GET", "/icons/comic/missing.png"),
            call("G09", "GET", "/icons/base/ideas.png"),
            call("G10", "GET", f"/day.json?day={day}"),
            call("G11", "GET", "/day.json"),
            call("G12", "GET", "/day-review.json"),
            call("G13", "GET", "/day-review.json?from=2026-01-01&to=2026-01-31"),
            call("G14", "GET", "/nothing-here"),
            call("G15", "GET", "/../XControlP.pyw"),
            call("G16", "GET", "/", host_header="evil.example"),
            call("G17", "GET", "/data.js", host_header=f"localhost:{port}"),
            call("P01", "POST", "/settings?lang=en", origin=False),
            call("P02", "POST", "/settings?lang=en", token="wrong-token"),
            call("P03", "POST", "/settings?lang=en", origin="http://evil.example"),
            call("P04", "POST", "/settings?lang=en", host_header="evil.example"),
            call("P05", "POST", "/nowhere"),
            call("P06", "POST", "/day/op", body=b""),
            call("P07", "POST", "/day/op", body=b"{}", kind="text/plain"),
            call("P08", "POST", "/request?kind=summary", length=600000),
            call("S01", "POST", "/settings?lang=en"),
            call("S02", "POST", "/settings?lang=xx"),
            call("S03", "POST", "/alerts?key=stale:website&state=dismissed"),
            call("S04", "POST", "/alerts?key=stale:shop&state=active"),
            call("S05", "POST", "/idea/flag?id=A-1&on=1"),
            call("S06", "POST", "/idea/flag?id=Z-99999&on=1"),
            call("S07", "POST", "/idea/service-remove?id=A-2"),
            call("S08", "POST", "/proposal?key=request-2026-01-14-090000-summary|p1&state=accepted"),
            call("S09", "POST", "/request?kind=summary", body={"today": day, "note": "oracle"}),
            call("S10", "POST", "/request?kind=nope", body={}),
            call("S11", "POST", "/day/op", body={"day": day, "ops": [
                {"op": "add", "kind": "task", "day": day, "title": "Oracle task"}]}),
            call("S12", "POST", "/day/op", body={"day": day, "ops": [
                {"op": "add", "kind": "stage", "day": day, "project": "website"},
                {"op": "add", "kind": "advance", "day": day, "project": "english", "amount": "1 lesson", "priority": "high"}]}),
            call("S13", "POST", "/day/op", body={"day": day, "ops": [
                {"op": "status", "id": "00000000000000000000000000000001", "status": "done"}]}),
            call("S14", "POST", "/day/op", body={"day": day, "ops": [{"op": "add", "kind": "nope", "day": day}]}),
            call("S18", "POST", "/day/op", body={"day": day, "ops": [
                {"op": "add", "kind": "task", "day": day, "title": "Urgent?", "priority": "urgent"}]}),
            call("S19", "POST", "/day/op", body={"day": day, "ops": [
                {"op": "add", "kind": "stage", "day": day, "project": "website", "stage": 9}]}),
            call("S15", "GET", f"/day.json?day={day}"),
            call("S16", "GET", "/day-review.json?from=2026-01-01&to=2026-01-31"),
            call("S17", "GET", "/data.js"),
        ]
        server.shutdown()
        server.server_close()
        after = normal((work / "data.js").read_text(encoding="utf-8"))

        files = {}
        for path in sorted(work.rglob("*")):
            rel = path.relative_to(work)
            name = rel.as_posix()
            # SQLite files are left out: their header holds the SQLite library's version, which differs by machine
            if (not path.is_file() or name in program_files or "__pycache__" in rel.parts
                    or rel.name.startswith("day.db") or rel.suffix == ".db" or rel.name.endswith(".tmp")
                    or name in ("data.js",)):
                continue
            raw = path.read_bytes()
            try:
                # a text file (any name) is hashed after normalisation: line ends, <ROOT>, <TOKEN>, <SQLITE>
                raw = normal(raw.decode("utf-8")).encode("utf-8")
            except UnicodeDecodeError:
                pass
            files[name] = hashlib.sha256(raw).hexdigest()

        write_bytes(out / "data-js.txt", first_build.encode("utf-8"))
        write_bytes(out / "data-after-js.txt", after.encode("utf-8"))
        write_bytes(out / "responses.json", (json.dumps(replies, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8"))
        write_bytes(out / "files.json", (json.dumps(files, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------- driver

def run(program, data, out):
    env = dict(os.environ, PYTHONHASHSEED="0", PYTHONUTF8="1", PULT_DIGEST_REPO="")
    command = [sys.executable, "-B", str(pathlib.Path(__file__).resolve()), "_run", str(program), str(data), str(out)]
    done = subprocess.run(command, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        print(done.stdout[-4000:])
        print(done.stderr[-4000:])
        print(f"ERROR run failed for program {program}")
        sys.exit(2)


def compare(left, right, left_name, right_name, diff_file=None):
    differences = 0
    full = []                       # every line, without the screen's cut, for diff_file

    def say(line, screen=True):
        full.append(line)
        if screen:
            print(line[:302])

    for name in OUTPUTS:
        try:
            a = (left / name).read_bytes().replace(b"\r\n", b"\n")
            b = (right / name).read_bytes().replace(b"\r\n", b"\n")
        except OSError as error:
            say(f"FAIL {name}: {error}")
            differences += 1
            continue
        if a == b:
            say(f"PASS {name} ({len(a)} bytes, sha256 {hashlib.sha256(a).hexdigest()[:12]})")
            continue
        differences += 1
        say(f"FAIL {name} differs:")
        diff = difflib.unified_diff(a.decode("utf-8", "replace").splitlines(), b.decode("utf-8", "replace").splitlines(),
                                    left_name, right_name, lineterm="", n=1)
        for i, line in enumerate(diff):
            if i == 60:
                print("  … (the screen shows the first 60 lines" + (f"; all are in {diff_file})" if diff_file else ")"))
            say("  " + line, screen=i < 60)
    say("RESULT " + ("PASS" if differences == 0 else "FAIL"))
    if diff_file:
        write_bytes(diff_file, ("\n".join(full) + "\n").encode("utf-8"))
    return 0 if differences == 0 else 1


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if argv[:1] == ["_run"] and len(argv) == 4:
        run_once(pathlib.Path(argv[1]).resolve(), pathlib.Path(argv[2]).resolve(), pathlib.Path(argv[3]).resolve())
        return 0
    if argv[:1] == ["check"] and len(argv) == 3 and argv[1] == "--out":
        keep = pathlib.Path(argv[2])
        if keep.exists() and (not keep.is_dir() or any(keep.iterdir())):
            print(f"ERROR {keep} exists and is not an empty folder: give a new folder")
            return 2
        run(REPO, SAMPLE, keep)
        return compare(EXPECTED, keep, "expected", "actual", keep / "diff.txt")
    if argv == ["check"]:
        with tempfile.TemporaryDirectory(prefix="xcp-oracle-out-") as out:
            run(REPO, SAMPLE, pathlib.Path(out))
            return compare(EXPECTED, pathlib.Path(out), "expected", "actual")
    if argv == ["freeze"]:
        with tempfile.TemporaryDirectory(prefix="xcp-oracle-out-") as out:
            run(REPO, SAMPLE, pathlib.Path(out))
            EXPECTED.mkdir(parents=True, exist_ok=True)
            for name in OUTPUTS:
                write_bytes(EXPECTED / name, (pathlib.Path(out) / name).read_bytes())
            print(f"frozen into {EXPECTED}")
            return 0
    if argv[:1] == ["compare"]:
        options = dict(zip(argv[1::2], argv[2::2]))
        if not {"--old", "--new", "--data"} <= set(options) or len(argv) % 2 == 0:
            print(__doc__)
            return 2
        keep = options.get("--out")
        base = pathlib.Path(keep) if keep else pathlib.Path(tempfile.mkdtemp(prefix="xcp-oracle-cmp-"))
        run(pathlib.Path(options["--old"]), pathlib.Path(options["--data"]), base / "old")
        run(pathlib.Path(options["--new"]), pathlib.Path(options["--data"]), base / "new")
        code = compare(base / "old", base / "new", "old", "new", base / "diff.txt" if keep else None)
        if not keep:
            shutil.rmtree(base, ignore_errors=True)
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
