**English** · [Русский](../ru/assistant.md) · [עברית](../he/assistant.md)

# Working with an AI assistant

XControlP is made to be kept by talking. You tell your assistant what happened or what you want; the assistant changes the data files; the window shows the result within seconds. Any assistant that can read and write files on your computer will do, for example Claude Code, or the Claude desktop app with the XControlP folder connected.

1. [Connect the assistant](#1-connect-the-assistant)
2. [What you can ask](#2-what-you-can-ask)
3. [Which files the assistant may change](#3-which-files-the-assistant-may-change)
4. [Projects](#4-projects)
5. [Day plan](#5-day-plan)
6. [Requests and answers](#6-requests-and-answers)
7. [Reports](#reports)
8. [Research](#research)
9. [Ideas and translations](#9-ideas-and-translations)
10. [What leaves your computer](#10-what-leaves-your-computer)

## 1. Connect the assistant

- Give it access to the XControlP folder (and to your project folders, if it should read them).
- The rules for the assistant are in [`AGENTS.md`](../../AGENTS.md) in the root of the folder. Claude Code reads them by itself (through `CLAUDE.md`). For other assistants, put one line into their instructions, for example a Claude Project's instructions:

```
You keep my XControlP dashboard in C:\Users\<you>\XControlP. Before any change, read AGENTS.md in that folder and follow it.
```

## 2. What you can ask

- «Add a project: Kitchen renovation, group Home, stages: plan, order, install; we are at plan.»
- «The website design is done, move it to Build.»
- «Plan tomorrow: an English lesson, the report and the website stage.»
- «Mark the English lesson done and carry the report to tomorrow.»
- «Close today: 7, the site took longer than planned.»
- «Review the request.» (after you pressed **Request a day summary** or **Request proposals**)
- «Write this week's report.»
- «Add an idea: a monthly newsletter for customers.»
- «Translate the new project names into English and Hebrew.»

## 3. Which files the assistant may change

| File | The assistant… |
|---|---|
| `projects.json`, `translations.json` | edits them, after a backup |
| idea files (`ideas/IDEAS.md` and the others in `ideas_files`) | edits them |
| `day.db` | **never opens it**; changes the day plan only through `day.py` |
| `answers/` | writes answers to requests |
| `requests/` | only reads |
| `research/`, `reports/` (or your report folders) | writes entries and reports |
| `data.js`, `auto.json`, `day.json`, `calendar.json`, `settings.json`, `alerts.json`, `proposals.json`, `flags.json`, `ideas-history.json` | does not change them: the program writes them |
| `google-client.json`, `google-token*.json` | never reads, copies or sends them: they are your keys |

Before changing a data file, the assistant copies it into a dated backup folder, for example `_backups/2026-11-12 before new project/` (folders starting with `_` are ignored by git).

## 4. Projects

The fields are described in [Setup, section 3](setup.md#3-projectsjson-groups-projects-stages). When a project moves:

- `current` becomes the number of the new stage (counted from 0);
- `last_move` becomes today's date;
- an event is added at the top of `history`: `{"date": "…", "project": "<id>", "text": "…"}`.

Projects with a `source` move by sync; the assistant does not move them by hand.

After an edit, check the file: `python XControlP.pyw --build`, then `data.js` must start with `window.BOARD = {` (with an error it holds `BOARD_ERROR` and the reason). While the window is open, the program rebuilds `data.js` by itself.

## 5. Day plan

The day plan lives in `day.db`, and only the program writes it. The assistant uses `day.py`: it checks each request with the same code as the program and puts it into `day-inbox/`. The program applies it within about 10 seconds while the window is open, otherwise at the next start, and writes the result to `day-inbox/applied/<name>.result.json`.

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

A task ID has 32 characters; `add` and `show` print it. The default day is today on this computer's clock.

## 6. Requests and answers

When you press **Request a day summary** or **Request proposals**, the program writes `requests/request-YYYY-MM-DD-HHMMSS-<kind>.json`:

```json
{"format": "pult-request", "id": "request-2026-11-12-173714-summary", "kind": "summary",
 "created": "2026-11-12T17:37", "lang": "en",
 "snapshot": {"today": "…", "day_plan": [], "alerts": [], "projects": [], "week": {},
              "waiting_requests": [], "open_proposals": []}}
```

When you write «review the request», the assistant:

1. reads the clock (the time in the answer must be a time it read, never a guess);
2. finds the request without an answer (the window shows it as waiting);
3. reads the snapshot and, if needed, your project files and reports;
4. writes `answers/answer-<request id>.json`:

```json
{
 "format": "pult-answer", "version": 1,
 "request": "request-2026-11-12-173714-summary",
 "kind": "summary",
 "written": "2026-11-12T19:05",
 "original": "en",
 "title":   {"en": "Day summary", "ru": "Сводка дня", "he": "סיכום היום"},
 "summary": {"en": "…", "ru": "…", "he": "…"},
 "blocks": [
  {"type": "points", "title": {"en": "Done", "ru": "Сделано", "he": "בוצע"},
   "items": [{"en": "…", "ru": "…", "he": "…"}]}
 ],
 "proposals": [
  {"id": "p1", "text": {"en": "…", "ru": "…", "he": "…"}, "why": {"en": "…", "ru": "…", "he": "…"}, "project": "website"}
 ]
}
```

- Every text is an object with `en`, `ru` and `he`; all three are required.
- `kind` is `summary` or `proposals`; `summary`, `why` and `project` are optional; a proposal `id` uses Latin letters, digits and dashes.
- Blocks are the same as in reports (below).

5. checks the file: `python tools/answer_check.py XControlP.pyw answers/<file>` must print `OK`.

A broken answer is not lost: the window shows it with the reason.

## Reports

A report is a Markdown file (`Weekly report 1–7.11.2026.md`, `Monthly report 2026-11.md`) in the reports folder ([Setup, section 7](setup.md#7-reports-research-and-digests)). A data file with the same name and `.json` lets the window draw it:

```json
{
 "format": "pult-report", "version": 1, "original": "en",
 "start": "2026-11-01", "end": "2026-11-07",
 "summary": {"en": "…", "ru": "…", "he": "…"},
 "rating": 8,
 "kpis": [{"id": "tasks", "value": 23}, {"id": "done_pct", "value": 74}],
 "categories": [
  {"id": "summary", "title": {"en": "Summary", "ru": "Итог", "he": "סיכום"}, "blocks": []},
  {"id": "risks", "title": {"en": "Risks", "ru": "Риски", "he": "סיכונים"}, "blocks": []}
 ]
}
```

- `kpis` ids: `commits`, `repos`, `tasks`, `done_pct`, `day_rating`, `lessons`, `ideas_new`, `hq_rating`. The window compares them with the previous report.
- Category ids with their own icon: `summary`, `tech`, `study`, `services`, `day`, `code`, `ideas`, `resources`, `decisions`, `risks`, `proposals`, `rating`; any other id works without an icon. Items in `risks` and `proposals` get the **To the day plan** button.

Blocks (`T` is a text object with `en`, `ru`, `he`; a title is optional unless shown):

| Block | Fields |
|---|---|
| `text` | `text: T` |
| `points` | `items: [T, …]` |
| `list` | `items: [{"title": T, "text": T}, …]` (numbered) |
| `table` | `columns: [T, …]`, `rows: [[cell, …], …]`, optional `total: [cell, …]`; a cell is a number or `T` |
| `bar` | `title: T`, `items: [{"label": T, "value": number}, …]`, optional `unit`, `note` |
| `line` | `title: T`, `items: [{"label": T, "value": number}, …]` |
| `stack` | `title: T`, `keys: [{"label": T}, …]`, `items: [{"label": T, "values": [number, …]}, …]` |
| `quotes` | `items: [{"date": "…", "topic": T, "text": T, "verbatim": true}, …]` |

## Research

`research/research.json`:

```json
{
 "research": [
  {
   "id": "market-2026-11", "date": "2026-11-12", "kind": "market", "original": "en",
   "title": {"en": "…", "ru": "…", "he": "…"},
   "text": {"en": "market-2026-11-en.md", "ru": "market-2026-11-ru.md", "he": "market-2026-11-he.md"},
   "sources": [{"lang": "en", "file": "market-2026-11-notes.md", "name": {"en": "Notes", "ru": "Заметки", "he": "הערות"}}],
   "services": ["A-1"]
  }
 ]
}
```

The `.md` files lie in `research/` next to `research.json`. `services` links the research to ideas marked as services.

## 9. Ideas and translations

- Ideas: add a row to the summary table and a section `## A-3. Title` in the idea file, by default `ideas/IDEAS.md` ([Setup, section 5](setup.md#5-ideas)). Change the status in both places.
- Translations: for every new data text (project name, stage, event, group), add its English and Hebrew versions to `translations.json` (the key is the text exactly as written).

The assistant ends each change with one line: what it changed and where.

## 10. What leaves your computer

The dashboard works on your computer. Its small web server answers only this computer (`127.0.0.1`), only the dashboard window, and only with the key issued at each start. Your data leaves the computer only through what you connect:

| What you connect | What leaves the computer |
|---|---|
| Google Calendar (optional) | the program signs in to Google and downloads your events; it never writes to the calendar |
| Git repositories (projects whose progress comes from git) | **Sync data** runs `git fetch`; nothing is pushed (a project with `"fetch": false` is read only from the computer) |
| A digests repository (optional, `digest_repo`) | **Sync data** pulls new digests; your «interesting» and «useful» marks are committed and pushed to that repository |
| An AI assistant | a cloud assistant (for example Claude) sends what it reads to its provider: data files, the project folders you open to it, your messages; a local model keeps them on the computer |

Give the assistant only the folders it needs. The assistant never reads your Google keys (`google-client.json`, `google-token*.json`), see [section 3](#3-which-files-the-assistant-may-change).
