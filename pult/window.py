# -*- coding: utf-8 -*-
"""XControlP — the window, the first start and main(). Moved unchanged from XControlP.pyw."""
import os
import pathlib
import subprocess
import sys
import threading
import webbrowser
from .config import (IDEAS_DEFAULT, IDEAS_TEMPLATE, PAGE, SOURCE, TEMPLATE)


# ---------------------------------------------------------------- запуск

def edge():
    names = [
        (os.environ.get("ProgramFiles(x86)"), r"Microsoft\Edge\Application\msedge.exe"),
        (os.environ.get("ProgramFiles"), r"Microsoft\Edge\Application\msedge.exe"),
        (os.environ.get("LOCALAPPDATA"), r"Microsoft\Edge\Application\msedge.exe"),
    ]
    for base, tail in names:
        if base:
            path = pathlib.Path(base) / tail
            if path.is_file():
                return str(path)
    return None


def open_window(url):
    browser = edge()
    if browser:
        subprocess.Popen([browser, f"--app={url}", "--start-maximized"], close_fds=True)
    else:
        webbrowser.open(url)


def first_start():
    """Первый запуск: projects.json нет, а шаблон есть — копия шаблона становится projects.json.
    Существующий projects.json не перезаписывается никогда (файл открывается в режиме «x»)."""
    if SOURCE.exists() or not TEMPLATE.is_file():
        return
    try:
        with open(SOURCE, "xb") as out:
            out.write(TEMPLATE.read_bytes())
    except OSError:
        return               # уже есть или не записать — build() покажет причину в окне
    if IDEAS_TEMPLATE.is_file() and not IDEAS_DEFAULT.exists():
        try:
            IDEAS_DEFAULT.parent.mkdir(exist_ok=True)
            with open(IDEAS_DEFAULT, "xb") as out:
                out.write(IDEAS_TEMPLATE.read_bytes())
        except OSError:
            pass


def main():
    first_start()
    build()
    LAST_STAMPS[0] = stamps()
    if "--build" in sys.argv:
        return
    try:
        server = Pult()
    except OSError:
        open_window(PAGE.as_uri())          # как раньше: окно из файла, без кнопки синхронизации
        return
    threading.Thread(target=watchdog, args=(server,), daemon=True).start()
    threading.Thread(target=calendar_keeper, daemon=True).start()
    threading.Thread(target=day_keeper, daemon=True).start()
    open_window(f"http://{server.host}/")
    server.serve_forever()
    server.server_close()


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .calendar_glue import (calendar_keeper)  # noqa: E402
from .build import (LAST_STAMPS, build, stamps)  # noqa: E402
from .day_glue import (day_keeper)  # noqa: E402
from .server import (Pult, watchdog)  # noqa: E402
