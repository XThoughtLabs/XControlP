# -*- coding: utf-8 -*-
"""Repository checks, run by CI on every push and before every commit (Python 3.10+, standard library only).

1. Every tracked Python file (.py, .pyw) compiles. Nothing is written: no __pycache__.
2. No tracked file is a data file: no tracked path matches a pattern of .gitignore.
3. Every tracked .json file parses.

    python -B tools/check_repo.py

Exit 0: all checks pass. Exit 1: a check failed. Exit 2: git could not list the tracked files.
"""
import fnmatch
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def tracked_files():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                             check=True, capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR cannot list the tracked files with git: {error}")
        sys.exit(2)
    return [p for p in out.decode("utf-8").split("\0") if p]


def ignore_patterns():
    patterns = []
    for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "!")):
            patterns.append(line)
    return patterns


def matching_pattern(path, patterns):
    """The .gitignore pattern a tracked path falls under, or None."""
    parts = path.split("/")
    for pattern in patterns:
        if pattern.endswith("/"):                       # a folder: any folder on the way
            name = pattern.rstrip("/")
            if any(fnmatch.fnmatchcase(part, name) for part in parts[:-1]):
                return pattern
        elif "/" in pattern.strip("/"):                 # a path from the root
            if fnmatch.fnmatchcase(path, pattern.lstrip("/")):
                return pattern
        elif fnmatch.fnmatchcase(parts[-1], pattern.lstrip("/")):   # a file name anywhere
            return pattern
    return None


def main():
    files = tracked_files()
    failures = []

    python_files = [f for f in files if f.endswith((".py", ".pyw"))]
    for name in python_files:
        try:
            compile((ROOT / name).read_bytes(), name, "exec")
        except (SyntaxError, ValueError) as error:
            failures.append(f"compile {name}: {error}")
    print(f"compile: {len(python_files)} Python files checked")

    patterns = ignore_patterns()
    for name in files:
        pattern = matching_pattern(name, patterns)
        if pattern:
            failures.append(f"data file {name} is tracked (matches .gitignore pattern {pattern!r})")
    print(f"data files: {len(files)} tracked files checked against {len(patterns)} .gitignore patterns")

    json_files = [f for f in files if f.endswith(".json")]
    for name in json_files:
        try:
            json.loads((ROOT / name).read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            failures.append(f"json {name}: {error}")
    print(f"json: {len(json_files)} files checked")

    for failure in failures:
        print("FAIL " + failure)
    print("RESULT " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
