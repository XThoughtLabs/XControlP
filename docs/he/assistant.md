[English](../en/assistant.md) · [Русский](../ru/assistant.md) · **עברית**

# עבודה עם עוזר בינה מלאכותית

XControlP נבנה כדי שינהלו אותו בשיחה. אתם אומרים לעוזר מה קרה או מה אתם רוצים; העוזר משנה את קובצי הנתונים; החלון מציג את התוצאה תוך שניות. מתאים כל עוזר שיודע לקרוא ולכתוב קבצים במחשב שלכם, למשל Claude Code, או אפליקציית Claude למחשב עם תיקיית XControlP מחוברת.

1. [לחבר את העוזר](#1-לחבר-את-העוזר)
2. [מה אפשר לבקש](#2-מה-אפשר-לבקש)
3. [אילו קבצים העוזר רשאי לשנות](#3-אילו-קבצים-העוזר-רשאי-לשנות)
4. [פרויקטים](#4-פרויקטים)
5. [תוכנית היום](#5-תוכנית-היום)
6. [בקשות ותשובות](#6-בקשות-ותשובות)
7. [דוחות](#דוחות)
8. [מחקרים](#מחקרים)
9. [רעיונות ותרגומים](#9-רעיונות-ותרגומים)

## 1. לחבר את העוזר

- נותנים לו גישה לתיקיית XControlP (ולתיקיות הפרויקטים, אם הוא צריך לקרוא אותן).
- הכללים לעוזר נמצאים ב-[`AGENTS.md`](../../AGENTS.md) בשורש התיקייה. Claude Code קורא אותם לבד (דרך `CLAUDE.md`). לעוזרים אחרים מוסיפים שורה אחת להוראות שלהם, למשל להוראות של פרויקט ב-Claude:

```
You keep my XControlP dashboard in C:\Users\<you>\XControlP. Before any change, read AGENTS.md in that folder and follow it.
```

## 2. מה אפשר לבקש

- «תוסיף פרויקט: שיפוץ המטבח, קבוצת בית, שלבים: תכנון, הזמנה, התקנה; אנחנו בתכנון.»
- «העיצוב של האתר מוכן, תעביר אותו לבנייה.»
- «תכנן את מחר: שיעור אנגלית, הדוח ושלב האתר.»
- «תסמן שהשיעור באנגלית בוצע ותעביר את הדוח למחר.»
- «תסגור את היום: 7, האתר לקח יותר זמן ממה שחשבנו.»
- «נתח את הבקשה.» (אחרי שלחצתם **לבקש סיכום יום** או **לבקש הצעות**)
- «תכתוב את הדוח של השבוע.»
- «תוסיף רעיון: ניוזלטר חודשי ללקוחות.»
- «תתרגם את שמות הפרויקטים החדשים לאנגלית ולרוסית.»

## 3. אילו קבצים העוזר רשאי לשנות

| קובץ | העוזר… |
|---|---|
| `projects.json`, `translations.json` | עורך אותם, אחרי גיבוי |
| קובצי רעיונות (`ideas/IDEAS.md` והאחרים שב-`ideas_files`) | עורך אותם |
| `day.db` | **אף פעם לא פותח אותו**; משנה את תוכנית היום רק דרך `day.py` |
| `answers/` | כותב תשובות לבקשות |
| `requests/` | רק קורא |
| `research/`, `reports/` (או תיקיות הדוחות שלכם) | כותב רשומות ודוחות |
| `data.js`, `auto.json`, `day.json`, `calendar.json`, `settings.json`, `alerts.json`, `proposals.json`, `flags.json`, `ideas-history.json` | לא משנה אותם: התוכנה כותבת אותם |
| `google-client.json`, `google-token*.json` | אף פעם לא קורא, מעתיק או שולח אותם: אלה המפתחות שלכם |

לפני שינוי של קובץ נתונים העוזר מעתיק אותו לתיקיית גיבוי עם תאריך, למשל `_backups/2026-11-12 before new project/` (git מתעלם מתיקיות שמתחילות ב-`_`).

## 4. פרויקטים

השדות מתוארים ב[הגדרה, סעיף 3](setup.md#3-projectsjson-קבוצות-פרויקטים-שלבים). כשפרויקט מתקדם:

- `current` הופך למספר השלב החדש (סופרים מ-0);
- `last_move` הופך לתאריך של היום;
- בראש `history` נוסף אירוע: `{"date": "…", "project": "<id>", "text": "…"}`.

פרויקטים עם `source` זזים בסנכרון; העוזר לא מזיז אותם ביד.

אחרי עריכה בודקים את הקובץ: `python XControlP.pyw --build`, ואז `data.js` צריך להתחיל ב-`window.BOARD = {` (כשיש שגיאה יש בו `BOARD_ERROR` והסיבה). כשהחלון פתוח, התוכנה בונה את `data.js` מחדש בעצמה.

## 5. תוכנית היום

תוכנית היום נשמרת ב-`day.db`, ורק התוכנה כותבת אותה. העוזר משתמש ב-`day.py`: הוא בודק כל בקשה באותו קוד כמו התוכנה ושם אותה ב-`day-inbox/`. התוכנה מחילה אותה תוך כ-10 שניות כשהחלון פתוח, אחרת בהפעלה הבאה, וכותבת את התוצאה ל-`day-inbox/applied/<name>.result.json`.

```
python day.py projects                                   projects, their ids and stages
python day.py show [--day 2026-11-12]                    the plan of a day and requests still waiting
python day.py add --day D --project english --amount "1 lesson" [--priority high|normal|low] [--note TEXT]
python day.py add --day D --project website --stage [N]   finish stage N (numbered as in the window, from 1)
python day.py add --day D --task "Call the bank" [--project ID]
python day.py plan --day D --file plan.json [--replace]  a whole day from a JSON list of tasks
python day.py status ID done|partial|not_done|active|planned|removed [--note TEXT]
python day.py note ID TEXT    priority ID high|normal|low    carry ID [--to D]    restore ID
python day.py edit ID [--stage N] [--amount TEXT] [--title TEXT]
python day.py order --day D ID ID ID …                   new order of all tasks of the day
python day.py day-note --day D TEXT                      the day's note
python day.py close --day D --rating 1..10 [--note TEXT] close the day
python day.py reopen --day D    carry-open --day D       reopen a day · carry all unfinished tasks to the next day
python day.py result [NAME]                              result of a request
```

למשימה יש מזהה (ID) של 32 תווים; `add` ו-`show` מדפיסים אותו. יום ברירת המחדל הוא היום לפי השעון של המחשב הזה.

## 6. בקשות ותשובות

כשלוחצים **לבקש סיכום יום** או **לבקש הצעות**, התוכנה כותבת `requests/request-YYYY-MM-DD-HHMMSS-<kind>.json`:

```json
{"format": "pult-request", "id": "request-2026-11-12-173714-summary", "kind": "summary",
 "created": "2026-11-12T17:37", "lang": "he",
 "snapshot": {"today": "…", "day_plan": [], "alerts": [], "projects": [], "week": {},
              "waiting_requests": [], "open_proposals": []}}
```

כשכותבים «נתח את הבקשה», העוזר:

1. קורא את השעון (הזמן בתשובה הוא רק זמן שנקרא, אף פעם לא ניחוש);
2. מוצא את הבקשה בלי תשובה (החלון מציג אותה כממתינה);
3. קורא את תמונת המצב, ואם צריך, גם את קובצי הפרויקטים והדוחות שלכם;
4. כותב `answers/answer-<request id>.json`:

```json
{
 "format": "pult-answer", "version": 1,
 "request": "request-2026-11-12-173714-summary",
 "kind": "summary",
 "written": "2026-11-12T19:05",
 "original": "he",
 "title":   {"he": "סיכום היום", "en": "Day summary", "ru": "Сводка дня"},
 "summary": {"he": "…", "en": "…", "ru": "…"},
 "blocks": [
  {"type": "points", "title": {"he": "בוצע", "en": "Done", "ru": "Сделано"},
   "items": [{"he": "…", "en": "…", "ru": "…"}]}
 ],
 "proposals": [
  {"id": "p1", "text": {"he": "…", "en": "…", "ru": "…"}, "why": {"he": "…", "en": "…", "ru": "…"}, "project": "website"}
 ]
}
```

- כל טקסט הוא אובייקט עם `he`, `en` ו-`ru`; שלושתם חובה.
- `kind` הוא `summary` או `proposals`; `summary`, `why` ו-`project` לא חובה; ה-`id` של הצעה באותיות לטיניות, ספרות ומקפים.
- הבלוקים זהים לאלה שבדוחות (בהמשך).

5. בודק את הקובץ: `python tools/answer_check.py XControlP.pyw answers/<file>` צריך להדפיס `OK`.

תשובה פגומה לא הולכת לאיבוד: החלון מציג אותה עם הסיבה.

## דוחות

דוח הוא קובץ Markdown (`Weekly report 1–7.11.2026.md`, `Monthly report 2026-11.md`) בתיקיית הדוחות ([הגדרה, סעיף 7](setup.md#7-דוחות-מחקרים-וסיכומים)). קובץ נתונים באותו שם עם הסיומת `.json` מאפשר לחלון לצייר אותו:

```json
{
 "format": "pult-report", "version": 1, "original": "he",
 "start": "2026-11-01", "end": "2026-11-07",
 "summary": {"he": "…", "en": "…", "ru": "…"},
 "rating": 8,
 "kpis": [{"id": "tasks", "value": 23}, {"id": "done_pct", "value": 74}],
 "categories": [
  {"id": "summary", "title": {"he": "סיכום", "en": "Summary", "ru": "Итог"}, "blocks": []},
  {"id": "risks", "title": {"he": "סיכונים", "en": "Risks", "ru": "Риски"}, "blocks": []}
 ]
}
```

- מזהי `kpis`: `commits`, `repos`, `tasks`, `done_pct`, `day_rating`, `lessons`, `ideas_new`, `hq_rating`. החלון משווה אותם לדוח הקודם.
- מזהי קטגוריות עם סמל משלהן: `summary`, `tech`, `study`, `services`, `day`, `code`, `ideas`, `resources`, `decisions`, `risks`, `proposals`, `rating`; כל מזהה אחר עובד, בלי סמל. לפריטים ב-`risks` וב-`proposals` יש כפתור **לתוכנית היום**.

בלוקים (`T` הוא אובייקט טקסט עם `he`, `en`, `ru`; כותרת לא חובה, אלא אם צוין אחרת):

| בלוק | שדות |
|---|---|
| `text` | `text: T` |
| `points` | `items: [T, …]` |
| `list` | `items: [{"title": T, "text": T}, …]` (ממוספר) |
| `table` | `columns: [T, …]`, `rows: [[cell, …], …]`, לא חובה `total: [cell, …]`; תא הוא מספר או `T` |
| `bar` | `title: T`, `items: [{"label": T, "value": number}, …]`, לא חובה `unit`, `note` |
| `line` | `title: T`, `items: [{"label": T, "value": number}, …]` |
| `stack` | `title: T`, `keys: [{"label": T}, …]`, `items: [{"label": T, "values": [number, …]}, …]` |
| `quotes` | `items: [{"date": "…", "topic": T, "text": T, "verbatim": true}, …]` |

## מחקרים

`research/research.json`:

```json
{
 "research": [
  {
   "id": "market-2026-11", "date": "2026-11-12", "kind": "market", "original": "he",
   "title": {"he": "…", "en": "…", "ru": "…"},
   "text": {"he": "market-2026-11-he.md", "en": "market-2026-11-en.md", "ru": "market-2026-11-ru.md"},
   "sources": [{"lang": "he", "file": "market-2026-11-notes.md", "name": {"he": "הערות", "en": "Notes", "ru": "Заметки"}}],
   "services": ["A-1"]
  }
 ]
}
```

קובצי ה-`.md` נמצאים ב-`research/` לצד `research.json`. `services` מקשר את המחקר לרעיונות שסומנו כשירותים.

## 9. רעיונות ותרגומים

- רעיונות: מוסיפים שורה לטבלת הסיכום ופסקה `## A-3. Title` בקובץ הרעיונות, כברירת מחדל `ideas/IDEAS.md` ([הגדרה, סעיף 5](setup.md#5-רעיונות)). את הסטטוס משנים בשני המקומות.
- תרגומים: לכל טקסט חדש בנתונים (שם פרויקט, שלב, אירוע, קבוצה) מוסיפים גרסה באנגלית ובעברית ל-`translations.json` (המפתח הוא הטקסט בדיוק כפי שנכתב).

בסוף כל שינוי העוזר כותב שורה אחת: מה שינה ואיפה.
