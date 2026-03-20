# Worklog

## 2026-03-20 16:35 - Rule Bootstrap

- Scanned `D:\Lush-Temp-Mail` and confirmed repo currently contains only static UI files with no backend/toolchain.
- Created root `AGENTS.md` with current repo rules and regression checklist.
- Created project memory docs: `PROJECT_CONTEXT.md`, `DECISIONS.md`, `WORKLOG.md`, `CHANGELOG.md`.
- Recorded target domain `lush.congmail.top` and the catch-all requirement for arbitrary `@congmail.top` addresses.

## 2026-03-20 17:20 - Backend + VPS runtime

- Added FastAPI backend under `backend/` with admin session auth, SQLite persistence, IMAP sync loop, alias auto-discovery, OTP/link extraction, and API endpoints for alias/message management.
- Replaced static mock frontend data with real API-driven admin UI in root `index.html`, `app.js`, `style.css`.
- Added repo hygiene and toolchain files: `.gitignore`, `requirements.txt`, `Dockerfile`, `backend/AGENTS.md`, `deploy/AGENTS.md`.
- Added VPS deploy assets under `deploy/`: `.env.example`, `docker-compose.vps.yml`, helper scripts, Caddy snippet, README.
- Verified local syntax/tests: `python -m py_compile`, `node --check app.js`, `pytest backend/tests/test_parser.py` pass.
- Created `.venv` locally and installed runtime/test dependencies for verification.
- Uploaded app to VPS at `/opt/lush-temp-mail/app`, created runtime `.env`, installed `lushtempmail` helper, and started container on `127.0.0.1:8012`.
- Enabled live catch-all on mail stack by updating `postfix-virtual.cf` to route `@congmail.top` into `contact@congmail.top`, preserving existing direct addresses/aliases.
- Updated shared Caddy config on VPS to add internal route for `lush.congmail.top`.
- Verified live technical flow with a real probe mail: unknown alias `probed1ef7ec7@congmail.top` was auto-created from inbound mail, message stored, OTP `482911` and verify link extracted correctly.
- Remaining external step: add DNS record for `lush.congmail.top -> 82.197.71.6` so Caddy can obtain public TLS cert and serve the app publicly.

## 2026-03-20 17:32 - Public proxy fix

- Diagnosed public `502` after DNS cutover: shared Caddy for `spoticheck` runs inside Docker, so upstream `127.0.0.1:8012` pointed to the Caddy container itself instead of the temp-mail app on the host.
- Updated deploy config to use `host.docker.internal:8012` and added `extra_hosts: host.docker.internal:host-gateway` for the Caddy service.
- Synced the same fix into `deploy/Caddyfile.snippet` and `deploy/README.md` of `Lush-Temp-Mail` to avoid future redeploy regressions.

## 2026-03-20 17:36 - Shared proxy network fix

- Confirmed `host.docker.internal` resolved from Caddy but still failed because temp-mail app was published only on host loopback `127.0.0.1:8012`.
- Switched deploy strategy to the cleaner cross-compose approach: app now joins external Docker network `shared_proxy` with alias `lushtempmail-app`.
- Updated Caddy upstream target to `lushtempmail-app:8010`, removing the need for a host-published app port.

## 2026-03-20 17:46 - Admin credential helper

- Added `deploy/scripts/set_admin_credentials.sh` to update `ADMIN_USERNAME` and `ADMIN_PASSWORD` inside `deploy/.env` then redeploy the app automatically.
- Extended `lushtempmail` helper with `set-admin` subcommand and installed the updated helper on VPS.
- Verified on VPS: `bash -n`, `lushtempmail --help`, `lushtempmail set-admin --help`, and a no-op credential update using the current admin values all succeeded.
- Prepared user-facing cheat-sheet update so admin login and the new command are easy to find.

## 2026-03-20 16:55 - IMAP live sync recovery

- Reproduced the live issue where mail to `hoang123@congmail.top` reached the mail server but did not appear in the temp-mail dashboard.
- Confirmed the temp-mail container was using a stale IMAP path and that the host/public route for `mail.congmail.top` was not a reliable way to reach the mailserver from this container stack.
- Updated deploy defaults/docs to keep `IMAP_HOST=mail.congmail.top` and changed `deploy/docker-compose.vps.yml` so `lushtempmail-app` joins external network `mailstack_default` in addition to `shared_proxy`.
- Synced the deploy files to VPS, redeployed the app, and verified on the live UI that alias `hoang123@congmail.top` and message `opt` are now visible.

## 2026-03-20 17:03 - Auto refresh and relative time ticker

- Added frontend auto-refresh while the admin tab is visible, with a silent refresh path that preserves the currently opened message instead of resetting the detail pane.
- Added a separate relative-time ticker so labels like `Vừa xong` and `14 phút trước` update on screen without requiring a manual refresh.
- Lowered the recommended backend IMAP sync interval from 20s to 10s in deploy defaults, then applied the same setting on the live VPS runtime.
- Synced the updated `app.js` and deploy docs to VPS, redeployed `lushtempmail-app`, and prepared the live app for a hard-reload test in the browser.

## 2026-03-20 17:18 - New mail emphasis and flicker removal

- Reworked the temp-mail frontend refresh flow so silent auto-refresh now performs a real `/api/sync` cycle every 8 seconds while the tab is visible.
- Added recent-message tracking on the client, with a visible `Email mới` badge and stronger row highlight for newly arrived mail in `Mail feed`.
- Replaced the old list re-render used by the relative-time ticker with DOM-only label updates, and stopped re-fetching/re-rendering the open message detail during silent refresh to remove the flicker effect.
- Synced the new `app.js` and `style.css` to VPS and redeployed `lushtempmail-app`.

## 2026-03-20 17:28 - Tone down new-mail styling

- Removed the bright row highlight and pulse animation from new-mail styling in the message list.
- Kept only the `Email mới` badge so the inbox returns to the previous neutral look.
- Synced the updated `style.css` to VPS and redeployed `lushtempmail-app`.

## 2026-03-20 17:35 - Publish repo to GitHub

- Prepared the local folder `D:\Lush-Temp-Mail` to become the source git repository for `shinemusicllc/Lush-Temp-Mail`.
- Verified the target GitHub remote is empty and re-checked `.gitignore` so runtime-only files like `deploy/.env`, `deploy/LOCAL_PASSWORDS.md`, `.venv/`, and `data/` stay out of version control.
- Proceeded to initialize git locally, commit the current application/deploy/docs state, and push it to GitHub.
