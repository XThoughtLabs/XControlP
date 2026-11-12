"""HQ helper: check an answer file with the Pult's own rule (check_answer) before it goes into the answers folder.
Usage: answer_check.py <path to XControlP.pyw> <answer.json> [<answer.json> ...]"""
import importlib.machinery, importlib.util, json, sys
loader = importlib.machinery.SourceFileLoader("pult_check", sys.argv[1]); spec = importlib.util.spec_from_loader("pult_check", loader)
m = importlib.util.module_from_spec(spec); loader.exec_module(m)
bad = 0
for path in sys.argv[2:]:
    try:
        problem = m.check_answer(json.load(open(path, encoding="utf-8-sig")))
    except (OSError, ValueError) as exc:
        problem = f"not readable: {exc}"
    print(("OK   " if not problem else "BAD  ") + path + ("" if not problem else " — " + problem)); bad += bool(problem)
sys.exit(1 if bad else 0)
