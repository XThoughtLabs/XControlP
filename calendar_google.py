# -*- coding: utf-8 -*-
"""Google Календарь для Пульта: вход через браузер и чтение событий. Только чтение.

Файлы рядом с Пультом — только на этом компьютере, в git не идут:
  google-client.json  ключ приложения из Google Cloud (тип Desktop app); кладёт владелец;
  google-token.json   разрешение первого аккаунта после входа; появляется сам;
  google-token-2.json, -3 …  разрешения других аккаунтов Google («+ Аккаунт» в Пульте);
  calendar.json       последние скачанные события; его читает окно Пульта.

Разрешение — только на чтение (calendar.readonly): Пульт не может ничего записать в календарь.
Пока приложение в Google в режиме «Testing», разрешение живёт 7 дней; потом Пульт попросит войти снова.
Вход — как у программ для компьютера: окно Google в браузере, ответ приходит на 127.0.0.1 (loopback) с PKCE.
Нужен только Python 3, без установки пакетов.
"""
import base64
import datetime
import hashlib
import http.server
import json
import os
import pathlib
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

HERE = pathlib.Path(__file__).resolve().parent
CLIENT = HERE / "google-client.json"
TOKEN = HERE / "google-token.json"          # первый аккаунт
EXTRA = "google-token-*.json"                # другие аккаунты: google-token-2.json, -3 …
CACHE = HERE / "calendar.json"
SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
API = os.environ.get("PULT_GCAL_API", "https://www.googleapis.com/calendar/v3")
DAYS_BACK = 62          # праздники: сколько дней назад брать события
DAYS_AHEAD = 183        # и сколько вперёд
HISTORY_FROM = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)  # личные календари — вся история с этой даты
PERSONAL_AHEAD = 730    # личные календари: на сколько дней вперёд
MAX_EVENTS = 20000      # предел событий одного календаря (защита от бесконечных повторов)
LOGIN_TIMEOUT = 300     # сколько ждать, пока владелец нажмёт «Разрешить»
TIMEOUT = 30

LOCK = threading.Lock()
LOGIN = {"running": False}


class CalendarError(Exception):
    """Ошибка, понятная владельцу: текст показывается в окне Пульта."""


class NeedLogin(CalendarError):
    """Разрешения нет или оно истекло — нужно войти в Google снова."""


def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def write_json(path, data):
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def client():
    data = read_json(CLIENT)
    if not data:
        raise CalendarError("Нет файла google-client.json в папке Пульта (ключ приложения из Google Cloud).")
    inner = data.get("installed") or data.get("web") or {}
    if not inner.get("client_id"):
        raise CalendarError("В google-client.json нет client_id — скачайте ключ приложения заново (тип Desktop app).")
    inner.setdefault("auth_uri", "https://accounts.google.com/o/oauth2/auth")
    inner.setdefault("token_uri", "https://oauth2.googleapis.com/token")
    return inner


def request(url, data=None, bearer=None):
    """HTTP-запрос к Google → JSON. Ошибку Google возвращает как (код, тело)."""
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if body is not None else "GET")
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    if bearer:
        req.add_header("Authorization", "Bearer " + bearer)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8") or "{}")
        except ValueError:
            detail = {}
        exc.detail = detail
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CalendarError(f"Нет связи с Google: {getattr(exc, 'reason', exc)}") from exc


def google_error(exc):
    detail = getattr(exc, "detail", {}) or {}
    err = detail.get("error")
    if isinstance(err, dict):
        return err.get("status") or str(err.get("code") or ""), err.get("message", "")
    return str(err or exc.code), str(detail.get("error_description", ""))


# ---------------------------------------------------------------- разрешение

def token_files():
    """Файлы разрешений по порядку: первый аккаунт, потом добавленные."""
    extra = sorted(HERE.glob(EXTRA), key=lambda p: (len(p.name), p.name))
    return ([TOKEN] if TOKEN.is_file() else []) + [p for p in extra if p.is_file()]


def connected():
    return bool(token_files())


def new_token_file():
    n = 2
    while (HERE / f"google-token-{n}.json").exists():
        n += 1
    return HERE / f"google-token-{n}.json"


def save_token(answer, old=None, path=TOKEN):
    token = dict(old or {})
    token["access_token"] = answer["access_token"]
    token["expires_at"] = time.time() + int(answer.get("expires_in", 3600))
    if answer.get("refresh_token"):
        token["refresh_token"] = answer["refresh_token"]
    token["scope"] = answer.get("scope", token.get("scope", SCOPE))
    token.setdefault("granted", now_text())
    token["updated"] = now_text()
    write_json(path, token)
    return token


def access_token(path=TOKEN):
    token = read_json(path)
    if not token or not token.get("refresh_token"):
        raise NeedLogin("Пульт ещё не подключён к Google Календарю — нужно войти.")
    if token.get("access_token") and token.get("expires_at", 0) > time.time() + 60:
        return token["access_token"]
    c = client()
    try:
        answer = request(c["token_uri"], {"client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                                          "refresh_token": token["refresh_token"], "grant_type": "refresh_token"})
    except urllib.error.HTTPError as exc:
        code, text = google_error(exc)
        if code in ("invalid_grant", "unauthorized_client", "400", "401"):
            raise NeedLogin("Разрешение Google истекло или отозвано — нужно войти снова. "
                            "Пока приложение в Google в режиме «Testing», так бывает раз в 7 дней.") from exc
        raise CalendarError(f"Google не обновил разрешение: {code} {text}".strip()) from exc
    return save_token(answer, token, path)["access_token"]


def account_of(access):
    """Почта аккаунта = id его основного календаря."""
    return request(API + "/calendars/primary", bearer=access).get("id", "")


def remember_account(path, email):
    token = read_json(path) or {}
    if email and token.get("account") != email:
        token["account"] = email
        write_json(path, token)


class Catcher(http.server.BaseHTTPRequestHandler):
    """Ловит ответ Google после «Разрешить»: http://127.0.0.1:<порт>/?code=…&state=…"""

    def log_message(self, *args):
        pass

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" not in query and "error" not in query:
            self.send_response(404)
            self.end_headers()
            return
        self.server.answer = {k: v[0] for k, v in query.items()}
        ok = "code" in query and query.get("state", [""])[0] == self.server.state
        text = ("Пульт получил разрешение на чтение календаря. Это окно можно закрыть." if ok else
                "Разрешение не получено. Закройте окно и попробуйте войти ещё раз из Пульта.")
        page = ('<!doctype html><meta charset="utf-8"><title>Пульт</title>'
                '<body style="font:16px system-ui;background:#0b0e14;color:#fff;display:grid;place-items:center;height:90vh">'
                f'<div style="max-width:520px;text-align:center"><h2>{"Готово" if ok else "Не получилось"}</h2><p>{text}</p></div>')
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def login(open_url=webbrowser.open, timeout=LOGIN_TIMEOUT, add=False, hint=""):
    """Окно Google в браузере → код на 127.0.0.1 → разрешение в файл этого аккаунта.
    add=True — добавить другой аккаунт; hint — почта аккаунта, которому нужно войти снова."""
    c = client()
    server = http.server.HTTPServer(("127.0.0.1", 0), Catcher)
    server.timeout = 1
    server.answer = None
    server.state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect = f"http://127.0.0.1:{server.server_address[1]}"
    url = c["auth_uri"] + "?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "select_account consent", "state": server.state,
        "code_challenge": challenge, "code_challenge_method": "S256", **({"login_hint": hint} if hint else {})})
    try:
        threading.Thread(target=open_url, args=(url,), daemon=True).start()
        deadline = time.monotonic() + timeout
        while server.answer is None and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    answer = server.answer
    if answer is None:
        raise CalendarError("Не дождался разрешения в окне Google (5 минут). Попробуйте войти ещё раз.")
    if answer.get("error"):
        raise CalendarError("Google не дал разрешение: " + ("вы нажали «Отмена»" if answer["error"] == "access_denied" else answer["error"]))
    if answer.get("state") != server.state:
        raise CalendarError("Ответ Google не совпал с запросом (state) — попробуйте войти ещё раз.")
    try:
        token = request(c["token_uri"], {"client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                                         "code": answer["code"], "code_verifier": verifier,
                                         "redirect_uri": redirect, "grant_type": "authorization_code"})
    except urllib.error.HTTPError as exc:
        code, text = google_error(exc)
        raise CalendarError(f"Google не выдал разрешение: {code} {text}".strip()) from exc
    if not token.get("refresh_token"):
        raise CalendarError("Google не выдал постоянное разрешение (refresh_token) — попробуйте войти ещё раз.")
    try:
        email = account_of(token["access_token"])
    except urllib.error.HTTPError as exc:
        code, text = google_error(exc)
        raise CalendarError(f"Google не сказал, какой это аккаунт: {code} {text}".strip()) from exc
    path = target_file(email, add)
    old = read_json(path) if path.is_file() else None
    save_token(token, {k: v for k, v in (old or {}).items() if k in ("granted",)}, path)
    remember_account(path, email)
    return email


def target_file(email, add):
    """Куда сохранить разрешение: файл этого же аккаунта (вход снова) или новый."""
    files = token_files()
    for path in files:
        if (read_json(path) or {}).get("account") == email:
            return path
    if not TOKEN.is_file():
        return TOKEN
    if not add:
        # старое разрешение без отметки аккаунта (до 06.10) — это вход снова в тот же аккаунт
        for path in files:
            if not (read_json(path) or {}).get("account"):
                return path
    return new_token_file()


def start_login(add=False, hint=""):
    """Кнопки «Войти в Google» и «+ Аккаунт»: вход идёт в фоне, окно Пульта не ждёт. Итог — в calendar.json."""
    with LOCK:
        if LOGIN["running"]:
            return False
        LOGIN["running"] = True

    def run():
        try:
            login(add=add, hint=hint)
            sync(after_login=True)
        except CalendarError as exc:
            mark(login_error=str(exc))
        except Exception as exc:                       # noqa: BLE001 — любая ошибка видна в окне
            mark(login_error=f"{type(exc).__name__}: {exc}")
        finally:
            LOGIN["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return True


# ---------------------------------------------------------------- события

def role_of(entry):
    cid = entry.get("id", "")
    if entry.get("primary"):
        return "main"
    if "#holiday@" in cid:
        return "holidays"
    return "other"


def name_of(entry, first=True):
    if entry.get("primary"):
        # основной календарь второго аккаунта называется по адресу почты
        return "Основной" if first else (entry.get("id", "").split("@")[0] or "Основной")
    return entry.get("summaryOverride") or entry.get("summary") or entry.get("id", "")


def rfc3339(moment):
    return moment.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(token, account="", first=True, seen=None):
    """Календари аккаунта, которые владелец видит в Google Календаре (выбраны), и их события:
    личные — вся история, праздники — окно дат. seen — id календарей, уже взятых из прежних аккаунтов
    (общий календарь не повторяется; праздники берутся только из первого аккаунта, где они есть)."""
    seen = seen if seen is not None else {"ids": set(), "holidays": False}
    listing, page = [], None
    while True:
        url = API + "/users/me/calendarList?" + urllib.parse.urlencode({"maxResults": 250, **({"pageToken": page} if page else {})})
        part = request(url, bearer=token)
        listing += part.get("items", [])
        page = part.get("nextPageToken")
        if not page:
            break
    chosen = [e for e in listing if e.get("primary") or e.get("selected")]
    now = datetime.datetime.now(datetime.timezone.utc)
    calendars, events = [], []
    for e in chosen:
        role = role_of(e)
        if e["id"] in seen["ids"] or (role == "holidays" and seen["holidays"]):
            continue
        if role == "main" and not first:
            role = "other"
        seen["ids"].add(e["id"])
        seen["holidays"] = seen["holidays"] or role == "holidays"
        calendars.append({"id": e["id"], "name": name_of(e, first), "role": role, "time_zone": e.get("timeZone", ""), "account": account})
        if role == "holidays":   # праздники повторяются каждый год — хватает окна вокруг сегодня
            window = {"timeMin": rfc3339(now - datetime.timedelta(days=DAYS_BACK)),
                      "timeMax": rfc3339(now + datetime.timedelta(days=DAYS_AHEAD))}
        else:                    # личные записи — все, как в Google Календаре
            window = {"timeMin": rfc3339(HISTORY_FROM),
                      "timeMax": rfc3339(now + datetime.timedelta(days=PERSONAL_AHEAD))}
        page, count = None, 0
        while count < MAX_EVENTS:
            params = {**window, "singleEvents": "true", "orderBy": "startTime", "maxResults": 2500, "showDeleted": "false"}
            if page:
                params["pageToken"] = page
            part = request(API + "/calendars/" + urllib.parse.quote(e["id"], safe="") + "/events?" + urllib.parse.urlencode(params), bearer=token)
            for ev in part.get("items", []):
                if ev.get("status") == "cancelled":
                    continue
                start, end = ev.get("start") or {}, ev.get("end") or {}
                all_day = "date" in start
                count += 1
                events.append({"cal": e["id"], "id": ev.get("id", ""),
                               "title": (ev.get("summary") or "").strip() or "(без названия)",
                               "start": start.get("date") or start.get("dateTime", ""),
                               "end": end.get("date") or end.get("dateTime", ""),
                               "all_day": all_day, "location": (ev.get("location") or "").strip()[:200]})
            page = part.get("nextPageToken")
            if not page:
                break
    return calendars, events


def mark(**fields):
    """Меняет поля состояния в calendar.json, не трогая скачанные события."""
    with LOCK:
        cache = read_json(CACHE) or {"version": 1, "calendars": [], "events": []}
        cache.update(fields)
        cache["checked"] = now_text()
        cache["rev"] = time.time()          # меняется при каждой записи — окно видит, что вход закончился
        write_json(CACHE, cache)
        return cache


def sync_account(path, first, seen):
    """Один аккаунт: (почта, календари, события). Ошибки — NeedLogin / CalendarError."""
    token = access_token(path)
    try:
        email = (read_json(path) or {}).get("account") or ""
        if not email:
            email = account_of(token)
            remember_account(path, email)
        calendars, events = fetch(token, email, first, seen)
    except urllib.error.HTTPError as exc:
        code, text = google_error(exc)
        if exc.code == 401:
            raise NeedLogin("Google не принял разрешение — нужно войти снова.") from exc
        if exc.code == 403 and "insufficient" in (text + code).lower():
            raise NeedLogin("У Пульта нет разрешения на календарь — войдите и отметьте доступ к календарю.") from exc
        raise CalendarError(f"Google ответил ошибкой: {exc.code} {text}".strip()) from exc
    return email, calendars, events


def sync(after_login=False):
    """Скачать события всех аккаунтов → calendar.json. Ошибка одного аккаунта не стирает его прежние события
    и не мешает остальным: окно показывает последние известные."""
    started = time.monotonic()
    files = token_files()
    if not files:
        msg = "Пульт ещё не подключён к Google Календарю — нужно войти."
        mark(need_login=True, error=msg)
        return {"ok": False, "need_login": True, "error": msg}
    old = read_json(CACHE) or {}
    seen = {"ids": set(), "holidays": False}
    accounts, calendars, events = [], [], []
    for i, path in enumerate(files):
        known = (read_json(path) or {}).get("account", "")
        try:
            email, cals, evs = sync_account(path, i == 0, seen)
            accounts.append({"account": email, "file": path.name, "ok": True, "need_login": False, "error": "",
                             "calendars": len(cals), "events": len(evs)})
        except CalendarError as exc:
            # прежние события этого аккаунта остаются (по отметке аккаунта в старом calendar.json)
            keep = [c for c in old.get("calendars", []) if known and c.get("account") == known and c["id"] not in seen["ids"]]
            if not known and i == 0:      # calendar.json до 06.10: календари без отметки — это первый аккаунт
                keep = [c for c in old.get("calendars", []) if not c.get("account") and c["id"] not in seen["ids"]]
            ids = {c["id"] for c in keep}
            seen["ids"] |= ids
            seen["holidays"] = seen["holidays"] or any(c.get("role") == "holidays" for c in keep)
            cals, evs = keep, [e for e in old.get("events", []) if e.get("cal") in ids]
            accounts.append({"account": known, "file": path.name, "ok": False, "need_login": isinstance(exc, NeedLogin),
                             "error": str(exc), "calendars": len(cals), "events": len(evs)})
        calendars += cals
        events += evs
    events.sort(key=lambda e: (e["start"], e["title"]))
    failed = [a for a in accounts if not a["ok"]]
    need = any(a["need_login"] for a in failed)
    error = " · ".join((a["account"] + ": " if a["account"] and len(accounts) > 1 else "") + a["error"] for a in failed)
    all_failed = len(failed) == len(accounts)
    with LOCK:
        write_json(CACHE, {"version": 2, "synced": old.get("synced", "") if all_failed else now_text(), "checked": now_text(), "rev": time.time(),
                           "need_login": need, "error": error, "login_error": "" if after_login else old.get("login_error", ""), "read_only": True,
                           "days_back": DAYS_BACK, "days_ahead": DAYS_AHEAD,
                           "history_from": HISTORY_FROM.date().isoformat(), "personal_ahead": PERSONAL_AHEAD,
                           "accounts": accounts, "calendars": calendars, "events": events})
    result = {"ok": not failed, "need_login": need, "error": error, "accounts": len(accounts),
              "calendars": len(calendars), "events": len(events), "seconds": round(time.monotonic() - started, 1)}
    return result


def setup():
    """Что есть на компьютере — для окна Пульта (без секретов)."""
    return {"client": CLIENT.is_file(), "token": connected(), "accounts": len(token_files()), "login_running": LOGIN["running"]}


def cache_age_minutes():
    cache = read_json(CACHE) or {}
    try:
        then = datetime.datetime.strptime(cache.get("synced", ""), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return (datetime.datetime.now() - then).total_seconds() / 60
