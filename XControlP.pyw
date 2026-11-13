# -*- coding: utf-8 -*-
"""XControlP: открывает пульт проектов в отдельном окне.

1. Читает projects.json (главный файл с данными) и собирает из него data.js,
   который читает окно «XControlP.html».
2. Идеи. Главный источник — общая база идей (ideas_db в projects.json: путь к ideas.db).
   Её ведут исполнители скриптом ideas.py, каждый — в своих таблицах своим ключом; Пульт открывает
   базу только для чтения (общие виды ideas, notes, status_log, links). Каждый отдел
   базы с идеями — свой подотдел раздела «Идеи», история статусов берётся из журнала базы,
   у идеи видны её проект и связи.
   Если база не указана, пуста или не читается — как раньше, файлы идей (ideas_files — список
   подотделов; старое поле ideas_file тоже понимается), только чтение, и своя история
   ideas-history.json (новая запись — только когда итог идеи изменился).
3. Если рядом есть auto.json (итог последней синхронизации), добавляет его: этапы проектов
   с источником, последнюю активность и новые события. projects.json при этом не меняется.
4. Запускает маленький сервер только внутри компьютера (127.0.0.1) и открывает через него
   «XControlP.html» в Microsoft Edge как отдельное окно (без адресной строки).
   Сервер нужен для кнопки «Синхронизировать данные»: она просит его запустить сборщик
   (collect.py). Запросы принимаются только от самого окна Пульта: по ключу, который выдаётся
   при запуске. Сервер закрывается сам, когда окно Пульта закрыто (10 минут без запросов).
   Если сервер не запустился, окно открывается как файл, как раньше, — без кнопки.
   При каждом запуске программы окно само один раз запускает ту же синхронизацию; кнопка остаётся для повторной.
   Вторая синхронизация, пока идёт первая, не начинается: окно отвечает «Синхронизация уже идёт».
   Первый запуск: если projects.json нет, а есть templates/projects.example.json, шаблон копируется
   в projects.json (готовый projects.json никогда не перезаписывается).

Ярлык «XControlP» на рабочем столе (его делает create_shortcut.pyw) запускает этот файл; значок — icon.ico.

5. Календарь: если рядом есть google-client.json, Пульт по кнопке «Войти в Google»
   получает разрешение только на чтение Google Календаря (calendar_google.py), скачивает события в
   calendar.json и показывает их в разделе «Календарь» вместе с рабочими событиями самого Пульта.
   Календарь обновляется при запуске, каждые 30 минут, пока окно открыто, и кнопкой синхронизации.
   google-client.json, google-token*.json и calendar.json — только на этом компьютере, в git не идут.
   Аккаунтов Google может быть несколько: «+ Аккаунт» в разделе «Календарь» (разрешения google-token-2.json, -3 …).

6. План дня: вкладка «План дня» — задачи на день из проектов и этапов
   («завершить этап», «продвинуться: 1 урок», своя задача), очередь и приоритет, отметки выполнения,
   «на завтра». Хранится в day.db (SQLite, day_store.py); открывает её только эта программа.
   Claude пишет не в базу, а запросы в папку day-inbox (скрипт day.py) — программа применяет их сама,
   пока окно открыто (каждые 10 секунд), и пишет копию для чтения day.json. Этапы проектов план дня не двигает.
   Вкладка «Итоги дней» (08.10.2026): день закрывается с оценкой от 1 до 10 и итогом словами; итоги недель и месяцев.
   Раздел «Статистика» (17.10.2026): неделя и месяц (потом квартал и год) — план дня, движение проектов, уроки,
   идеи и коммиты, со сравнением с прошлым периодом. Уроки и коммиты по дням собирает сборщик (кнопка синхронизации).

7. Языки (этап Пульта «Меню языков», 08.10.2026): русский, английский, иврит (окно зеркальное).
   Выбор языка — settings.json (кнопки в меню слева, сохраняет эта программа). Надписи окна — i18n.js,
   данные (названия проектов, групп, этапов, описания, события) — translations.json; нет перевода — по-русски.

8. Сводки: раздел «Сводки» — ежедневные сводки новостей из git-репозитория сводок (digest_store.py).
   Репозиторий задаёт переменная окружения PULT_DIGEST_REPO или ключ digest_repo в projects.json; не задан —
   раздел пуст и ни одна команда git не запускается. Отметки «интересно» и «полезно» Пульт
   пишет в репозиторий и сразу делает коммит и push; кнопка синхронизации забирает новые сводки.

9. Исследования: папка research рядом с Пультом — реестр research.json
   и тексты .md (каждая запись на трёх языках и исходные документы). Пульт только читает их и кладёт
   в data.js; раздел «Исследования» и подраздел «Исследование рынка» в карточке услуги. Записи добавляет штаб.

10. Отчёты: недельные отчёты штаба из папки reports/weekly рядом с Пультом (другое место — reports_dir
   в projects.json). Даты недели берутся
   из имени файла «Weekly report ДД–ДД.ММ.ГГГГ.md» (старое «Недельный отчёт …» тоже понимается); месячные отчёты
   — из reports/monthly (при своём reports_dir — из папки Monthly рядом с ней), «Monthly report ГГГГ-ММ.md»
   (другое место — monthly_reports_dir); если папка лежит в git-репозитории с GitHub, ссылка ведёт на GitHub; отчёт, которого нет
   в origin/main, помечается «не отправлен». Пульт только читает: git ls-tree, без записи.

Окно само перечитывает data.js каждые 20 секунд. Пока окно открыто, программа пересобирает
data.js, как только изменились projects.json, база или файлы идей, — перезапускать ничего не нужно.
Нужен только Python 3, без установки пакетов.

Только собрать data.js, не открывая окно:  python XControlP.pyw --build
Взять первый файл идей из другого места:   python XControlP.pyw --build --ideas=ПУТЬ
"""
import os
import pathlib
import sys

# pythonw запускается без консоли: всё, что пишется в консоль, уходит в никуда.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# The code lives in the package pult/ beside this file (stage 2 of the modules plan). Its folder goes
# first on the import path, because tools load this file by path (the oracle, the empty-start check,
# answer_check).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pult.config import (HERE, SOURCE, TEMPLATE, IDEAS_TEMPLATE, IDEAS_DEFAULT, TARGET, AUTO, HISTORY, PAGE,
                         COLLECTOR, SYNC_LOG, CALENDAR_MODULE, CALENDAR_FILES, CALENDAR_EVERY, TRANSLATIONS,
                         SETTINGS, ALERTS, ALERT_STATES, ALERT_KEEP_DAYS, RESEARCH_DIR, RESEARCH,
                         RESEARCH_FILE, RESEARCH_MAX, REPORT_NAME, MONTH_NAME, GIT_NO_WINDOW, REPORT_MAX,
                         FLAGS, IDEA_ID, LANGS, DAY_MODULE, REQUESTS_DIR, ANSWERS_DIR, PROPOSALS,
                         REQUEST_KINDS, REQUEST_BODY_LIMIT, PROPOSAL_STATES, ANSWER_MAX, PROPOSAL_KEY,
                         DAY_COPY, CARRY_OPEN, DIGEST_MODULE, DAY_EVERY, DAY_BODY_LIMIT, IDLE_SECONDS)  # noqa: E402,F401
from pult.ideas import (ROW, HEAD, LABEL, DATE, clean, iso, read_ideas, idea_path, idea_sources, idea_kind,
                        update_history, read_idea_sets, ideas_db_path, outcome, read_ideas_db)  # noqa: E402,F401
from pult.settings import (read_translations, SETTING_DEFAULTS, setting_choices, read_settings,
                           save_settings, read_alerts, save_alert, read_carried, ICONS_DIR, ICON_PATH,
                           STYLE_ID, icon_styles)  # noqa: E402,F401
from pult.calendar_glue import (_GCAL, gcal, calendar_data, calendar_connected, calendar_sync_quiet,
                                calendar_login, calendar_add, calendar_sync_now, calendar_keeper)  # noqa: E402,F401
from pult.hq_exchange import (write_request, lang_text, check_answer, read_answers, read_requests,
                              read_proposal_marks, save_proposal)  # noqa: E402,F401
from pult.services import (read_services, write_services, known_idea_ids, query_id, save_flag, remove_service)  # noqa: E402,F401
from pult.research import (read_research_text, read_research)  # noqa: E402,F401
from pult.reports import (reports_dir, monthly_dir, month_dates, git_root, github_base, report_dates,
                          git_names_on_origin, read_report_files, read_report_folder, read_reports,
                          reveal_report)  # noqa: E402,F401
from pult.build import (read_auto, merge_auto, build, SYNC_LOCK, watched_files, stamps, LAST_STAMPS,
                        rebuild_if_changed, effective_stages)  # noqa: E402,F401
from pult.sync import (run_sync, SYNC_GATE, STARTUP_SYNC, STARTUP_LOCK, sync_request, startup_sync_request)  # noqa: E402,F401
from pult.digests import (_DIGEST, DIGEST_PROBLEM, digest_repo, digest_store, digest_view, digest_stamp,
                          digest_sync, digest_mark)  # noqa: E402,F401
from pult.day_glue import (_DAY, DAY_PROBLEM, day_store, day_error, day_view, day_review, day_op, day_keeper)  # noqa: E402,F401
from pult.server import (Pult, FILES, Handler, watchdog)  # noqa: E402,F401
from pult.window import (edge, open_window, first_start, main)  # noqa: E402,F401


if __name__ == "__main__":
    main()
