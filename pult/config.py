# -*- coding: utf-8 -*-
"""XControlP — paths, names and limits. Moved unchanged from XControlP.pyw."""
import os
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent.parent   # the program's folder: pult/ lies inside it
SOURCE = HERE / "projects.json"
TEMPLATE = HERE / "templates" / "projects.example.json"   # пустой projects.json для первого запуска
IDEAS_TEMPLATE = HERE / "templates" / "IDEAS.example.md"  # пустой файл идей для первого запуска
IDEAS_DEFAULT = HERE / "ideas" / "IDEAS.md"               # файл идей, который создаёт первый запуск
TARGET = HERE / "data.js"
AUTO = HERE / "auto.json"
HISTORY = HERE / "ideas-history.json"
PAGE = HERE / "XControlP.html"
COLLECTOR = HERE / "collect.py"
SYNC_LOG = HERE / "sync-last-error.txt"
CALENDAR_MODULE = HERE / "calendar_google.py"
CALENDAR_FILES = [HERE / "calendar.json", HERE / "google-client.json", HERE / "google-token.json"]
CALENDAR_EVERY = 30 * 60        # как часто обновлять календарь, пока окно открыто
TRANSLATIONS = HERE / "translations.json"
SETTINGS = HERE / "settings.json"
ALERTS = HERE / "alerts.json"           # отметки тревог: «в починке» и «убрана» (кнопки в окне)
ALERT_STATES = ("repair", "dismissed")
ALERT_KEEP_DAYS = 365                   # отметки старше года — забываются
RESEARCH_DIR = HERE / "research"       # отдел исследований: research.json (реестр) и тексты .md; Пульт только читает
RESEARCH = RESEARCH_DIR / "research.json"
RESEARCH_FILE = re.compile(r"^[^/\\:]+\.md$")
RESEARCH_MAX = 2_000_000   # байт на один текст
REPORT_NAME = re.compile(r"^(?:Weekly report|Недельный отчёт) (\d{1,2})(?:\.(\d{1,2}))?[–-](\d{1,2})\.(\d{1,2})\.(\d{4})\.md$")
MONTH_NAME = re.compile(r"^Monthly report (\d{4})-(\d{2})\.md$")
GIT_NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # git без мигающих окон консоли
REPORT_MAX = 2_000_000   # байт на текст отчёта и на его файл данных
FLAGS = HERE / "flags.json"             # реестр услуг: услуга закреплена, флажок снимается и ставится (кнопки в карточке идеи); база идей не меняется
IDEA_ID = re.compile(r"^[A-Z]{1,3}-\d{1,5}$")
LANGS = ("ru", "en", "he")
DAY_MODULE = HERE / "day_store.py"
REQUESTS_DIR = HERE / "requests"         # запросы штабу: кнопки «Запросить сводку дня» и «Запросить предложения»
ANSWERS_DIR = HERE / "answers"           # ответы штаба (pult-answer, три языка); пишет штаб
PROPOSALS = HERE / "proposals.json"     # отметки предложений: принято (в плане дня) или отклонено
REQUEST_KINDS = ("summary", "proposals")
REQUEST_BODY_LIMIT = 512 * 1024
PROPOSAL_STATES = ("accepted", "declined")
ANSWER_MAX = 2_000_000
PROPOSAL_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}\|[a-z0-9][a-z0-9-]{0,39}$")
DAY_COPY = HERE / "day.json"            # копия плана дня для чтения (пишет хранилище плана дня)
CARRY_OPEN = ("planned", "active", "partial", "not_done")
DIGEST_MODULE = HERE / "digest_store.py"
DAY_EVERY = 10                  # как часто смотреть запросы Claude в day-inbox, пока окно открыто
DAY_BODY_LIMIT = 64 * 1024
IDLE_SECONDS = 600
