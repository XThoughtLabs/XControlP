**English** · [Русский](../ru/using.md) · [עברית](../he/using.md)

# Using the XControlP window

The menu is on the left, the chosen section on the right. Sections with no data (for example Ideas with no idea files) do not appear in the menu.

## Top bar and bottom bar

- **Period** (for example «Last 30 days»): the time span for activity charts and counts.
- **Sync data**: reads progress from your repositories and progress files, refreshes the calendar and digests. It also runs once at every start. A second sync does not start while one is running.
- **Save report**: opens the print dialog; choose «Save as PDF» to keep the current screen as a document.
- The bottom bar sums up today: projects in progress, on pause and stopped, and the alert state («All calm» or the number of alerts).

## Overview and groups

**Overview** shows all projects (except the personal-growth group `Развитие`): counts by status, stage moves in the period, average progress, activity by day, progress of each project and where your attention went. The **Day summary** card shows the assistant's summary of today, if you asked for one (see [Proposals](#proposals-and-requests-to-the-assistant)).

Each group from `projects.json` has its own menu entry with the projects of that group. A project card shows its stages, the current stage, the status, days since the last move, recent events and its link. Projects with a progress source show where the data came from.

The **Focus** card in the menu shows the project in focus (`focus` in `projects.json`, or the first project in progress).

## Alerts

An alert appears when:

| Alert | When |
|---|---|
| Project stopped | status `stop` |
| No movement | a project in progress has not moved for more than 14 days |
| Long pause | a project on pause for more than 30 days |
| Carried over to tomorrow | a day-plan task was carried over 3 times or more |
| Weekly report not pushed | two days after the week ended, the report is still not on `origin/main` |
| Decisions waiting | ideas with the status «решение» wait more than 30 days |

Each alert has buttons: **Repair** (you are on it: the alert stays visible but is not counted), **Remove** (hide it; it comes back if the situation changes, for example the number of carry-overs grows), **Restore**, and **To the day plan** (adds a task for today).

## Day plan

The day's tasks, top to bottom in your order.

- **Add to plan** (right side): choose a project (or «No project, own task»), then what to do: **Finish a stage**, **Advance** (how far, for example «1 lesson»), or **Own task**. Set the priority: Important, Normal, Later.
- Mark a task: in progress, done, partly done, not done; ↑ ↓ change the order; ⚑ the priority.
- **To tomorrow** carries a task to the next day; the new task remembers where it came from.
- **Day summary**: a few words about the day, for yourself.
- **Close the day**: rate the day from 1 to 10 and write the result. Closed days appear in **Day results** with week and month summaries.
- The **Through Claude** card: you can also tell your assistant «plan tomorrow: …» or «let's plan the day like this…». The assistant adds the tasks through `day.py`; they appear marked «Claude» within about 10 seconds (or at the next start if the window was closed).

The day plan never moves a project's stage: stages move only in `projects.json` or through a progress source.

## Calendar

Your Google calendars (read-only) together with the dashboard's own work events. Events that run over midnight are shown as nights. To connect: see [Setup, section 6](setup.md#6-google-calendar).

## Statistics

Week, month, quarter (by weeks) and year (by months): day-plan tasks and how many were done, project movement, lessons, new ideas and commits, compared with the previous period.

## Ideas, services, idea statistics

- **Ideas**: one subsection per idea file. Filter by status; open an idea to see its notes and history. Ids of other ideas in a text are links.
- **Services**: ideas you marked with the flag as services. Taking the flag off keeps the idea in Services; **Remove from services** takes it out completely. Idea files are never changed.
- **Idea statistics**: how many ideas are in each status and how that changes over time.
- **Overall level**: one score from 0 to 100% made of three parts: movement of projects in progress, ideas carried out, and ideas sorted.

## Research, reports, digests

- **Research**: entries your assistant prepared, each in three languages, with its source documents.
- **Reports**: weekly and monthly reports. If a report has a data file, the window shows its figures and charts by category, and arrows compare it with the previous report; **Original** shows the Markdown text. In the «Risks» and «Proposals» categories every item has **To the day plan**. **Show in folder** opens the file in Explorer.
- **Digests** (if configured): daily news digests; mark items «interesting» or «useful».

## Proposals and requests to the assistant

The dashboard does not talk to an AI model itself. Instead:

1. Press **Request a day summary** or **Request proposals** (on the Overview or in Proposals). The program saves a snapshot of the dashboard to `requests/`.
2. In the chat with your assistant, write «review the request».
3. The assistant reads the request and writes an answer to `answers/`. The window picks it up by itself; **Load proposals** does it at once.
4. A day summary appears on the Overview. Proposals appear in **Proposals**: **To the day plan** turns one into a task for today, **Decline** hides it, **Restore** brings it back.

How the assistant does its part: [Working with an assistant](assistant.md).

## Settings

The ☰ button next to the language opens **Settings**: language (English, Russian, Hebrew; in Hebrew the window is mirrored), icon style (comic stickers or simple symbols), theme (dark or light), text size and accent colour. They are saved in `settings.json`.

In the window, «HQ» (штаб) means your assistant's chat.
