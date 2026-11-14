# -*- coding: utf-8 -*-
"""XControlP — the local server: the server class and the request handler. Moved unchanged from XControlP.pyw."""
import datetime
import http.server
import json
import secrets
import time
import traceback
import urllib.parse
from .config import (DAY_BODY_LIMIT, HERE, IDLE_SECONDS, PAGE, REQUEST_BODY_LIMIT, SYNC_LOG)


# ---------------------------------------------------------------- локальный сервер

class Pult(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.token = secrets.token_urlsafe(24)
        self.host = f"127.0.0.1:{self.server_address[1]}"
        self.seen = time.monotonic()


FILES = {"/data.js": ("data.js", "text/javascript; charset=utf-8"),
         "/i18n.js": ("i18n.js", "text/javascript; charset=utf-8"),
         "/css/pult.css": ("css/pult.css", "text/css; charset=utf-8"),
         "/js/01-core.js": ("js/01-core.js", "text/javascript; charset=utf-8"),
         "/js/02-idea-stats.js": ("js/02-idea-stats.js", "text/javascript; charset=utf-8"),
         "/js/03-performance.js": ("js/03-performance.js", "text/javascript; charset=utf-8"),
         "/js/04-calendar.js": ("js/04-calendar.js", "text/javascript; charset=utf-8"),
         "/js/05-day-plan.js": ("js/05-day-plan.js", "text/javascript; charset=utf-8"),
         "/js/06-day-results.js": ("js/06-day-results.js", "text/javascript; charset=utf-8"),
         "/js/07-stats.js": ("js/07-stats.js", "text/javascript; charset=utf-8"),
         "/js/08-reports.js": ("js/08-reports.js", "text/javascript; charset=utf-8"),
         "/js/09-research.js": ("js/09-research.js", "text/javascript; charset=utf-8"),
         "/js/10-settings.js": ("js/10-settings.js", "text/javascript; charset=utf-8"),
         "/icon.svg": ("icon.svg", "image/svg+xml"),
         "/icon.ico": ("icon.ico", "image/x-icon")}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "Pult/1"

    def log_message(self, *args):
        pass

    def allowed(self):
        self.server.seen = time.monotonic()
        if self.headers.get("Host") != self.server.host:      # защита от чужих сайтов под видом 127.0.0.1
            self.send_error(403)
            return False
        return True

    def send(self, status, body, kind, cache="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.allowed():
            return
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            page = PAGE.read_text(encoding="utf-8")
            meta = f'<meta name="pult-token" content="{self.server.token}">'
            page = page.replace("</head>", meta + "\n</head>", 1)
            self.send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/day-review.json":
            result, status = day_review(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
            self.send(status, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif path == "/day.json":
            result, status = day_view(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
            self.send(status, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif path in FILES:
            if path == "/data.js":
                rebuild_if_changed()
            name, kind = FILES[path]
            try:
                self.send(200, (HERE / name).read_bytes(), kind)
            except OSError:
                self.send_error(404)
        elif ICON_PATH.match(path):
            # картинка запоминается окном, чтобы меню не мигало при обновлении
            sid, name = ICON_PATH.match(path).groups()
            style = icon_styles().get(sid)
            try:
                if not style:
                    raise OSError(sid)
                body = (style["folder"] / (name + ".png")).read_bytes()
            except OSError:
                self.send_error(404)
                return
            self.send(200, body, "image/png", cache="private, max-age=86400")
        else:
            self.send_error(404)

    def do_POST(self):
        if not self.allowed():
            return
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
        actions = {"/sync": sync_request, "/sync/startup": startup_sync_request, "/calendar/login": lambda: calendar_login(query),
                   "/calendar/add": lambda: calendar_add(query), "/calendar/sync": calendar_sync_now,
                   "/settings": lambda: save_settings(query), "/alerts": lambda: save_alert(query),
                   "/digest/mark": lambda: digest_mark(query), "/idea/flag": lambda: save_flag(query),
                   "/idea/service-remove": lambda: remove_service(query), "/report/reveal": lambda: reveal_report(query),
                   "/proposal": lambda: save_proposal(query)}
        if path not in actions and path not in ("/day/op", "/request"):
            self.send_error(404)
            return
        if self.headers.get("Origin") != "http://" + self.server.host or \
                not secrets.compare_digest(self.headers.get("X-Pult-Token", ""), self.server.token):
            self.send_error(403)
            return
        if path in ("/day/op", "/request"):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            limit = DAY_BODY_LIMIT if path == "/day/op" else REQUEST_BODY_LIMIT
            if not 0 < length <= limit or not (self.headers.get("Content-Type") or "").startswith("application/json"):
                self.send_error(400)
                return
            if path == "/request":
                try:
                    result, status = write_request(query, self.rfile.read(length)), 200
                except OSError as exc:
                    result, status = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500
            else:
                result, status = day_op(self.rfile.read(length))
            self.server.seen = time.monotonic()
            self.send(status, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        try:
            result, status = actions[path](), 200
        except Exception as exc:
            report = traceback.format_exc()
            try:
                SYNC_LOG.write_text(datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + "\n\n" + report, encoding="utf-8")
            except OSError:
                pass
            result, status = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500
        self.server.seen = time.monotonic()
        self.send(status, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")


def watchdog(server):
    """Окно закрыто — запросов нет — сервер закрывается сам."""
    while True:
        time.sleep(30)
        if time.monotonic() - server.seen > IDLE_SECONDS and not SYNC_LOCK.locked():
            server.shutdown()
            return


# Neighbours are imported at the end: build() reads every area and the writers call build() again,
# so the modules refer to each other; by the time any function runs, these names exist.
from .settings import (ICON_PATH, icon_styles, save_alert, save_settings)  # noqa: E402
from .calendar_glue import (calendar_add, calendar_login, calendar_sync_now)  # noqa: E402
from .hq_exchange import (save_proposal, write_request)  # noqa: E402
from .services import (remove_service, save_flag)  # noqa: E402
from .reports import (reveal_report)  # noqa: E402
from .build import (SYNC_LOCK, rebuild_if_changed)  # noqa: E402
from .sync import (startup_sync_request, sync_request)  # noqa: E402
from .digests import (digest_mark)  # noqa: E402
from .day_glue import (day_op, day_review, day_view)  # noqa: E402
