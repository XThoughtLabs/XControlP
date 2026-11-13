# -*- coding: utf-8 -*-
"""XControlP — research files. Moved unchanged from XControlP.pyw."""
import json
from .config import (RESEARCH, RESEARCH_DIR, RESEARCH_FILE, RESEARCH_MAX)


def read_research_text(name):
    """Текст из папки research: только простое имя файла .md, без путей; файла нет или он слишком большой — пусто."""
    if not isinstance(name, str) or name.startswith(".") or not RESEARCH_FILE.match(name):
        return ""
    path = RESEARCH_DIR / name
    try:
        if path.resolve().parent != RESEARCH_DIR.resolve() or path.stat().st_size > RESEARCH_MAX:
            return ""
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def read_research():
    """Отдел исследований: research.json → записи (новые сверху) с текстами по языкам и исходными документами."""
    if not RESEARCH.exists():
        return {"entries": [], "error": ""}
    try:
        raw = json.loads(RESEARCH.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return {"entries": [], "error": f"research.json не читается: {exc}"}
    entries = []
    for item in raw.get("research", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        files = item.get("text") if isinstance(item.get("text"), dict) else {}
        texts = {lang: read_research_text(name) for lang, name in files.items()}
        sources = [{"lang": src.get("lang", ""), "file": src.get("file", ""), "name": src.get("name") if isinstance(src.get("name"), dict) else {},
                    "text": read_research_text(src.get("file"))} for src in item.get("sources") or [] if isinstance(src, dict)]
        entries.append({"id": str(item["id"]), "date": str(item.get("date", "")), "kind": item.get("kind", ""),
                        "services": [str(x) for x in item.get("services") or []], "version": str(item.get("version", "")),
                        "original": item.get("original", ""), "title": item.get("title") if isinstance(item.get("title"), dict) else {},
                        "answer": item.get("answer") if isinstance(item.get("answer"), dict) else {},
                        "text": {k: v for k, v in texts.items() if v}, "missing": [files[k] for k, v in texts.items() if not v],
                        "sources": sources})
    entries.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    return {"entries": entries, "error": ""}
