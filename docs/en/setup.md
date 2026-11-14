**English** · [Русский](../ru/setup.md) · [עברית](../he/setup.md)

# Setting up XControlP

1. [Install and first start](#1-install-and-first-start)
2. [Files in the folder](#2-files-in-the-folder)
3. [projects.json: groups, projects, stages](#3-projectsjson-groups-projects-stages)
4. [Progress that updates itself](#4-progress-that-updates-itself)
5. [Ideas](#5-ideas)
6. [Google Calendar](#6-google-calendar)
7. [Reports, research and digests](#7-reports-research-and-digests)
8. [Translations of your data](#8-translations-of-your-data)
9. [Updating XControlP](#9-updating-xcontrolp)
10. [When something does not work](#10-when-something-does-not-work)

## 1. Install and first start

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/) (keep the option that installs the `py` launcher).
2. Put XControlP in a folder of your own, for example `C:\Users\<you>\XControlP` (`git clone` or **Download ZIP**).
3. Double-click `create_shortcut.pyw`: it creates the desktop shortcut **XControlP**. If it cannot, it writes the reason to `shortcut-error.txt`.
4. Open the shortcut.

What happens at start:

- If there is no `projects.json`, it is created from `templates/projects.example.json` (an empty dashboard). An existing `projects.json` is never overwritten. At the same first start, an empty ideas file `ideas/IDEAS.md` is created from `templates/IDEAS.example.md`, so **Ideas** is in the menu from the start.
- The program builds `data.js` (what the window reads) from your files and starts a small web server that only this computer can reach (`127.0.0.1`). Requests are accepted only from the dashboard window, by a key issued at start.
- The window opens as an Edge app window. The program closes itself about 10 minutes after the window is closed.
- Sync runs once (see [section 4](#4-progress-that-updates-itself)).

While the window is open, the program rebuilds `data.js` as soon as `projects.json` or another data file changes, and the window rereads it every 20 seconds. You do not need to restart anything after an edit.

To rebuild `data.js` without opening a window: `python XControlP.pyw --build`.

## 2. Files in the folder

**The program** (comes with XControlP):

| File | What it is |
|---|---|
| `XControlP.pyw` | the program: builds the data, runs the local server, opens the window |
| `pult/` | the program's code, one file per area (ideas, settings, reports, server, window …); `XControlP.pyw` starts it |
| `XControlP.html`, `i18n.js` | the window and its labels in English and Hebrew |
| `css/`, `js/` | the window's styles and scripts (the scripts split by sections of the window); `XControlP.html` loads them |
| `collect.py` | sync: reads progress from repositories and progress files |
| `day_store.py`, `day.py`, `day_test.py` | the day plan: storage, the command-line tool for assistants, tests |
| `calendar_google.py` | Google Calendar sign-in and reading |
| `digest_store.py` | daily digests (optional) |
| `create_shortcut.pyw`, `start_fallback.cmd` | desktop shortcut, spare launcher |
| `icons/`, `icon.ico`, `icon.svg` | icons |
| `templates/projects.example.json`, `templates/IDEAS.example.md` | the empty starting `projects.json` and ideas file |
| `tools/answer_check.py` | checks an assistant's answer file before it goes into `answers/` |

**Your data** (created as you work; all of it is in `.gitignore`):

| File or folder | What it holds | Who writes it |
|---|---|---|
| `projects.json` | groups, projects, stages, history, settings of sources | you or your assistant |
| `translations.json` | English and Hebrew versions of your data texts | you or your assistant |
| `ideas/IDEAS.md` | your ideas (the ideas file created at the first start) | you or your assistant |
| `auto.json` | the last sync result | the program |
| `data.js` | everything the window shows | the program |
| `day.db`, `day.json` | the day plan (database and its read-only copy) | the program only |
| `day-inbox/` | day-plan requests from an assistant | the assistant, through `day.py` |
| `calendar.json`, `google-client.json`, `google-token*.json` | calendar events and Google access | the program; `google-client.json` is yours |
| `requests/`, `answers/`, `proposals.json` | requests to the assistant, its answers, your marks on proposals | the program, the assistant |
| `research/` | research entries and texts | the assistant |
| `reports/` | weekly and monthly reports (if you keep them here) | the assistant |
| `settings.json`, `alerts.json`, `flags.json`, `ideas-history.json` | window settings, alert marks, services, idea history | the program |

## 3. projects.json: groups, projects, stages

A small but complete example:

```json
{
 "updated": "2026-11-12",
 "focus": "website",
 "groups": ["Work", "Study", "Home"],
 "projects": [
  {
   "id": "website",
   "name": "Company website",
   "group": "Work",
   "status": "work",
   "about": "New site for the studio: design, build, publish.",
   "link": "https://example.com",
   "stages": ["Design", "Build", "Content", "Publish"],
   "current": 1,
   "last_move": "2026-11-10"
  },
  {
   "id": "english",
   "name": "English course",
   "group": "Study",
   "status": "pause",
   "stages": ["A01–A08: basics", "A09–A16: everyday talk", "A17–A24: writing"],
   "current": 0,
   "last_move": "2026-10-20"
  }
 ],
 "history": [
  {"date": "2026-11-10", "project": "website", "text": "Design approved"}
 ]
}
```

Fields of the file:

| Field | Meaning |
|---|---|
| `updated` | date of your last manual update (shown under the title) |
| `focus` | id of the project shown in the **Focus** card of the menu; empty: the first project in progress |
| `groups` | groups in menu order; each group gets its own menu entry |
| `projects` | the projects (below) |
| `history` | events, newest first: `date`, `project` (id), `text` |
| `ideas_files` | idea files ([section 5](#5-ideas)) |
| `reports_dir`, `monthly_reports_dir` | report folders ([section 7](#7-reports-research-and-digests)) |
| `digest_repo` | folder of the digests repository ([section 7](#7-reports-research-and-digests)) |

Fields of a project:

| Field | Meaning |
|---|---|
| `id` | short Latin id, unique: `website`, `english` |
| `name` | name shown in the window |
| `group` | one of `groups` |
| `status` | `work` (in progress), `pause`, `stop` (stopped), `plan` (planned); the Russian words `в работе`, `на паузе`, `остановлен`, `план` work too |
| `about` | one or two sentences about the project (optional) |
| `link` | a link shown on the project card, for example its board (optional) |
| `stages` | stage names in order |
| `current` | number of the stage in progress, counted **from 0**; all stages before it are done |
| `last_move` | date the stage last changed (alerts count days from it) |
| `source` | where progress comes from automatically ([section 4](#4-progress-that-updates-itself), optional) |
| `moves_with` | for an overall-plan project: ids of projects whose movement counts as its own (optional) |

Notes:

- A mistake in `projects.json` (a missing comma, for example) does not break the window: it shows the error text instead.
- A group named exactly `Развитие` is the personal-growth section: its projects have their own menu entry and are not counted in «All projects».
- Alerts: a project in progress with no movement for more than 14 days, a project on pause for more than 30 days, a stopped project. Projects with the status `plan` raise no alerts.

## 4. Progress that updates itself

Without a `source`, a project moves when you (or your assistant) change `current` and `last_move`. With a `source`, the **Sync data** button (and the start of the program) reads the progress for you. Sync never changes `projects.json`: it writes its result to `auto.json`, and the window combines the two. If the source shows a stage lower than the one you wrote by hand, your stage stays and a warning appears.

All sources accept `"since": "YYYY-MM-DD"`: events before that date are not added (useful when your history up to then is already written by hand).

**A progress file** (any project, no git needed):

```json
"source": {"kind": "progress", "path": "C:\\Users\\<you>\\Projects\\Garden\\PROGRESS.json", "since": "2026-11-01"}
```

`PROGRESS.json` in the project's folder:

```json
{
 "stages": ["Plan", "Buy", "Plant", "Harvest"],
 "current": 2,
 "stage_changed": "2026-11-08",
 "now": "Planting the beds on the south side",
 "events": [{"date": "2026-11-08", "text": "Plants bought"}]
}
```

`stages` must match the project's stages in `projects.json` exactly. An event «Урок 06 пройден» counts a lesson for the statistics.

**Stages from a git repository** (`kind: stages`): the stage names in `projects.json` start with an id and a colon, for example `G1: data model`, `G2: import`. A branch whose name holds `stage-g2` means stage G2 has started; its merge into the main branch means G2 is done. Optional fields: `file` (a stages file in the repository, `{"stages": [{"id": "g1", "date": "…", "merge_commit": "…"}]}`), `branch_pattern` (your own regular expression for stage ids in branch names), `"fetch": false` (do not fetch from the remote, read only what is on this computer).

```json
"source": {"kind": "stages", "repo": "C:\\Users\\<you>\\GitHub\\my-app", "since": "2026-11-01"}
```

**Lessons from a git repository** (`kind: lessons`), for courses: stage names start with a block of lesson codes, for example `A01–A08: basics`. A commit whose message holds a lesson code (`A05`) moves the course to that block; a commit «A01-A08 summary» (or «Итог модуля A01–A08») closes the block.

**Sync** runs `git fetch` (it never changes your working files), reads the sources and also counts commits per day in all repositories of the folders where your project repositories live (only the counts, for the statistics). Problems appear in the window; the last error is also written to `sync-last-error.txt`. If GitHub cannot be reached, sync uses what is already on the computer and says so.

## 5. Ideas

Ideas live in Markdown files. List them in `projects.json`; each file becomes a subsection of **Ideas**. From the first start there is one, `ideas/IDEAS.md`:

```json
"ideas_files": [
 {"id": "main", "title": "", "about": "", "path": "ideas/IDEAS.md"},
 {"id": "work", "title": "Work ideas", "about": "Ideas for the studio", "path": "C:\\Users\\<you>\\Notes\\WORK-IDEAS.md"}
]
```

A relative path is counted from the XControlP folder. With an empty `title`, the first subsection is called «Ideas» in every window language. If `ideas_files` is empty, the sections **Ideas**, **Our services** and **Ideas analytics** are hidden.

The file has a summary table and a section per idea:

```markdown
| ID | Date | Idea | Status |
|---|---|---|---|
| A-1 | 2026-11-01 | Newsletter for customers | идея |
| A-2 | 2026-11-05 | Move the site to a new host | в дорожной карте |

## A-1. Monthly newsletter for customers
- **Суть:** one letter a month with news and offers.
- **Статус:** идея
```

An idea id is a capital Latin letter, a dash and a number (`A-1`, `B-12`). Other ids written in the text (`see A-2`) become links.

The window sorts ideas by the first words of their status (today it recognises Russian words):

| Status starts with | Meaning |
|---|---|
| `сделано` | done |
| `в дорожной карте` | on the roadmap |
| `решение` | a decision that is not carried out yet |
| contains `исследовать` | to explore |
| `отказ` | dropped |
| `ждёт`, `отложено` | waiting |
| anything else | an idea |

The program only reads idea files. It keeps its own history of status changes in `ideas-history.json`. The **Services** section lists ideas you marked as services (the flag button on an idea; stored in `flags.json`).

Advanced: instead of files, `ideas_db` can point to an SQLite ideas base; the program opens it read-only. See `read_ideas_db` in `XControlP.pyw` for the views it expects.

## 6. Google Calendar

Optional. XControlP reads your calendars and never writes to them (permission `calendar.readonly`).

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project, enable the **Google Calendar API**, set up the OAuth consent screen (you can keep it in Testing and add yourself as a test user).
2. **Google Auth Platform → Clients → Create client**, type **Desktop app**, then **Download JSON**.
3. Save the file as `google-client.json` in the XControlP folder.
4. In the window, open **Calendar** and press **Sign in to Google**. A browser window asks for permission; the answer comes back to the program on this computer.

Several accounts: **+ Account** in the Calendar section. While the Google app is in Testing mode, the permission lasts 7 days; then the dashboard asks you to sign in again. The calendar refreshes at start, every 30 minutes while the window is open, and with **Sync data**.

An event whose title holds `night` (or `ночн`, `לילה`) and starts at 00:00 is shown as the night from the previous day.

## 7. Reports, research and digests

**Reports.** Weekly reports are Markdown files named `Weekly report 1–7.11.2026.md` (or `Weekly report 28.10–3.11.2026.md`), monthly ones `Monthly report 2026-11.md`. By default they are read from `reports/weekly` and `reports/monthly` in the XControlP folder; set `reports_dir` and `monthly_reports_dir` in `projects.json` to read them from elsewhere (with your own `reports_dir` and no `monthly_reports_dir`, monthly reports are read from a folder `Monthly` next to it). A `.json` file with the same name may hold the report's figures and charts for the window; its format is in the [assistant guide](assistant.md#reports). If the reports folder is inside a git repository, a report that is not yet on `origin/main` is marked «not pushed», and two days after its week ends it becomes an alert.

**Research.** `research/research.json` lists research entries; their texts are `.md` files in the same folder. The format is in the [assistant guide](assistant.md#research).

**Digests (optional).** Daily news digests from a git repository of your own: set `digest_repo` in `projects.json` (or the environment variable `PULT_DIGEST_REPO`). The repository holds `digests/YYYY/MM/YYYY-MM-DD.json`; your marks «interesting» and «useful» go to `marks/YYYY/MM/YYYY-MM-DD.json`, and the program commits and pushes them itself. Without `digest_repo` the section stays empty and no git command runs.

## 8. Translations of your data

Write your data (project names, stages, events) in one language. The window's own labels are already translated. To see your data in the other window languages too, add `translations.json`:

```json
{
 "en": {"Сайт студии": "Studio website"},
 "he": {"Сайт студии": "אתר הסטודיו"}
}
```

The key is the text exactly as written in your data; a text with no translation is shown as written.

The week in the window starts on Sunday.

## 9. Updating XControlP

With git: `git pull` in the folder. Without git: download the new version and replace the program files (section 2, «the program»). Your data files are not part of XControlP and are not touched either way. Close the window first.

## 10. When something does not work

| What you see | What to do |
|---|---|
| The window opened as a page without the **Sync data** button | The local server did not start (another copy is running, or a firewall blocked it). Close all XControlP windows, wait a minute and open it again. |
| An error text instead of projects | `projects.json` has a mistake; the text names the line. |
| A sync problem in the window | Read the note; the last error is also in `sync-last-error.txt`. |
| No window at all | Run `start_fallback.cmd`; if Python is missing, install it (section 1). |
| The calendar asks to sign in again | Normal in Google's Testing mode (every 7 days). |
