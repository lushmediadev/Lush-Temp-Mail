# Project Brief

## Purpose
- `Lush-Temp-Mail` is a FastAPI + vanilla HTML/CSS/JS temp-mail app for checking inboxes on the configured mail domain.
- The core user flow is: enter an email alias, sync/list inbound messages, open message detail, inspect OTP/link/content quickly.
- Admin flow manages users and the broader inbox; user flow is a focused public-style lookup workspace behind login.

## System Shape
- Root static files (`index.html`, `app.js`, `style.css`) implement the admin shell.
- Root user files (`user.html`, `user.js`, `user.css`) implement the user inbox lookup and reader.
- `backend/app/` contains FastAPI routes, auth/session, SQLite persistence, IMAP sync, parsing, translation, and send helpers.
- `deploy/` contains VPS runtime scripts/config.

## Build / Test / Run
- Dev server: `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010 --reload`
- Tests: `.\.venv\Scripts\python.exe -m pytest -q`
- Python syntax: `Get-ChildItem .\backend\app\*.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }`
- Frontend syntax: `node --check .\app.js` and `node --check .\user.js`

## Global Invariants
- Keep the app vanilla: no bundler or frontend framework unless there is a clear reason.
- Do not require users to pre-create aliases before receiving mail; inbound mail must still auto-discover aliases.
- Preserve UTF-8 Vietnamese UI text.
- Keep UI changes close to the current LushMail visual language and avoid broad layout rewrites.

