# Rules for an AI assistant working in an XControlP folder

You help a person keep their XControlP dashboard: projects, day plan, ideas, requests and answers, reports, research.
The full guide is `docs/en/assistant.md` (also in `docs/ru/` and `docs/he/`). These rules always apply.

## Before you change anything

- Ask the person and wait for a clear yes, unless they have asked for this exact change.
- Copy every data file you are about to change into `_backups/YYYY-MM-DD <what>/` first.
- Read the clock by command before writing any date or time. Never write a time you have not read.

## Files

- `projects.json`, `translations.json`, the idea files, `answers/`, `research/`, the report folders: you may write them.
- `day.db`: never open it. Change the day plan only with `python day.py …` (see `docs/en/assistant.md`, section 5).
- `requests/`: read only.
- `data.js`, `auto.json`, `day.json`, `calendar.json`, `settings.json`, `alerts.json`, `proposals.json`, `flags.json`, `ideas-history.json`: the program writes them; do not change them.
- `google-client.json`, `google-token*.json`: secrets. Never read, copy, print or send them.
- The program files (`XControlP.pyw`, `pult/`, `XControlP.html`, `css/`, `js/`, `i18n.js`, `*.py`): change them only when the person asks for a change to the program itself.

## After a change

- `projects.json`: run `python XControlP.pyw --build`; `data.js` must start with `window.BOARD = {`.
- An answer: run `python tools/answer_check.py XControlP.pyw answers/<file>`; it must print `OK`.
- Every new text in the person's data gets English and Hebrew versions in `translations.json` when the window is used in those languages.
- Tell the person in one line what you changed and where.

## «Review the request»

Find the request in `requests/` that has no answer in `answers/`, read its snapshot, write `answers/answer-<request id>.json` in the `pult-answer` version 1 format with every text in `en`, `ru` and `he`, check it with `tools/answer_check.py`, and say in one line what you wrote.

## Privacy

Everything in this folder is the person's own data. Do not send it anywhere and do not put it into a public repository: the `.gitignore` of XControlP keeps the data files out of git, and it must stay that way.
