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

## 2026-03-20 18:22 - Clone repo and run local app

- Cloned `https://github.com/shinemusicllc/Lush-Temp-Mail` into `C:\Users\PC\Lush-Temp-Mail`.
- Read project rules/context from `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`, and `docs/WORKLOG.md` before local runtime setup.
- Created local virtual environment at `.venv` and installed dependencies from `requirements.txt`.
- Started the FastAPI app locally with `uvicorn backend.app.main:app --host 127.0.0.1 --port 8010`.
- Verified local health endpoint at `http://127.0.0.1:8010/api/health` returned status `ok`.
- Opened the local app URL in the default browser for immediate access.

## 2026-03-20 18:48 - Simplify local inbox layout for review

- Removed the orange hero cover and pulled the working layout directly under the sticky topbar.
- Removed alias management UI from the local dashboard sidebar and client-side logic, keeping the local review flow focused on inbox reading only.
- Added fixed footer pagination to the mail list area and implemented client-side page switching for the fetched message list.
- Kept the email list in its own scrollable pane so the topbar, filters, footer pagination, and detail pane stay stable while browsing mail.
- Verified frontend syntax with `node --check app.js` and reloaded the local app to confirm the simplified layout renders successfully.

## 2026-03-20 18:57 - Trim topbar and add warm favicon

- Removed the temporary `Mail Console` info card from the sidebar to keep only the inbox filter actions.
- Removed the topbar sync button and the admin avatar/name cluster so the header stays minimal around the logo only.
- Added a dedicated `favicon.svg` with a warm background and red mail icon, then linked it in the page head.
- Re-ran frontend syntax check and reloaded the local app to confirm the simplified chrome renders without JS errors.

## 2026-03-20 19:00 - Redesign favicon with lucide-like mail mark

- Reworked `favicon.svg` into a cleaner mail icon with thicker strokes and a simpler warm tile so it remains legible at tiny browser-tab sizes.
- Kept the visual language aligned with the app palette while reducing decorative details that made the previous favicon look noisy when scaled down.
- Reloaded the local app after the icon update to make the new tab asset available for preview.

## 2026-03-20 19:04 - Switch favicon to app logo mark

- Updated the page head so the browser tab now uses `logo.svg` directly as the favicon instead of the temporary custom `favicon.svg`.
- Aligned the tab icon with the exact logo mark already shown in the app header for a more consistent brand feel.

## 2026-03-20 19:14 - Deploy latest UI polish to VPS

- Connected to VPS `82.197.71.6` as `root` and confirmed the live app repo is at `/opt/lush-temp-mail/app`.
- Uploaded the current local UI files (`index.html`, `app.js`, `style.css`) plus updated project logs to the live repo copy on the server.
- Rebuilt and restarted the live Docker stack from `/opt/lush-temp-mail/app/deploy` with `docker compose --env-file .env -f docker-compose.vps.yml up -d --build`.
- Verified container `lushtempmail-app` came back healthy and that `/api/health` returned `status: ok` from inside the container.
- Verified the public app at `https://lush.congmail.top` reflects the new layout after login, including the simplified topbar/sidebar and working inbox pagination.

## 2026-03-20 19:35 - Inbox interaction polish and faster sync

- Updated backend message search so the main search now matches alias/recipient address in addition to sender, subject, and snippet.
- Added backend message deletion endpoint and frontend hover delete button, plus automatic suppression of messages older than 7 days during sync cleanup.
- Reworked the inbox row layout to show alias first, sender second, subject third, and switched avatar colors to deterministic random palettes per message seed.
- Reduced frontend auto-sync polling to 3 seconds while the tab is visible and changed live VPS runtime `MAIL_SYNC_INTERVAL_S` to `4` for faster IMAP pickup.
- Synced the updated frontend/backend files to VPS, rebuilt `lushtempmail-app`, and verified on the public app that alias search and the new row layout are live.

## 2026-03-20 20:17 - Important inbox group, 60-day retention, and composer polish

- Added `Quan trọng` filter end-to-end: SQLite auto-migration for `messages.important`, API toggle endpoint, hover star action in the inbox row, and star persistence in the live UI.
- Changed inbox row actions so the delete control now uses the same icon-only visual language as the mail tab icon, while OTP rows keep the star visible and the alias-first ordering remains intact.
- Added reply/forward composer UI inside the email detail pane with `To`, `CC`, `Subject`, and `Message` fields styled to match the current Tailwind-based shell.
- Changed alias lifetime defaults to `60 ngày` (`DEFAULT_ALIAS_HOURS=1440`) and message cleanup to `60 ngày` (`MESSAGE_RETENTION_DAYS=60`) for both local code and live VPS runtime.
- Updated root `AGENTS.md` build/test commands to be repo-relative instead of the stale `D:` path from the older local workspace.
- Verified locally with `node --check .\\app.js` and Python compile checks, then verified live at `https://lush.congmail.top` after login that `Quan trọng`, star toggle, icon-only delete, and the composer panel are present and working.

## 2026-03-20 20:36 - Detail pane layout polish and recent-badge stability

- Reworked the desktop reading pane to use the remaining right-side width instead of the old fixed 420px column, with a wider centered reader shell and calmer card spacing.
- Removed the awkward `Email actions` card from the top of the mail content and moved `Trả lời` / `Chuyển tiếp` into a dedicated action bar at the bottom of the detail flow.
- Adjusted the compose panel so reply/forward drafts now open inline above the bottom action bar, keeping `CC` and the Tailwind visual language intact.
- Changed recent-message tracking from per-filter comparison to session-wide seen-message tracking so switching between `Tất cả email` and `Có OTP` no longer marks old rows as `Email mới` again.
- Added render suppression for unchanged inbox lists, which keeps the same DOM rows across auto-refresh cycles and removes the hover flicker caused by unnecessary re-renders.
- Verified locally with `node --check .\\app.js`, then redeployed the frontend to VPS and confirmed on the live inbox that the detail pane is wider, the action bar sits at the bottom, filter switching keeps `Email mới` stable, and the first row node stays unchanged across auto-refresh when data does not change.

## 2026-03-20 20:40 - Push detail scroll to viewport edge and restore message-list width

- Removed the centered/max-width shell around the live app content so the desktop workspace now spans the full viewport width.
- Restored the message-list column to flexible width and changed the detail pane to a fixed responsive width anchored on the far right of the viewport.
- Kept the detail pane scroll on `#emailDetail`, which now sits flush with the page edge so the scrollbar is no longer stealing space from the email list side.
- Redeployed the updated `index.html` to VPS and verified on the live app that the detail pane reaches the viewport edge (`detailRightGap = 0`) while the email list regains its wider layout.

## 2026-03-20 20:44 - Revert desktop shell to centered layout from reference image

- Reverted the previous viewport-edge layout change after it diverged from the user's reference screenshot.
- Restored the centered desktop shell with `max-width: 1600px`, the inbox list back to the narrower fixed-width middle column, and the detail pane filling the remaining width inside that centered shell.
- Redeployed the reverted `index.html` to VPS and verified live that the shell is back to `1600px` wide with centered gutters, `mainWidth = 560`, and `detailWidth = 752`, matching the intended proportions more closely.

## 2026-03-20 20:48 - Match saved legacy layout file exactly

- Opened the user's saved reference file at `C:\Users\PC\Downloads\html lang=viscript src=chrome-exten.html` and compared the actual classes instead of estimating from screenshots.
- Confirmed the legacy proportions are `main = flex-1` and `#emailDetail = w-[420px]`, with the centered `max-w-[1600px]` shell preserved.
- Updated `index.html` to match that layout model exactly, then redeployed the app to VPS.
- Verified live after login that the shell is `1600px`, the inbox list is `892px`, and the detail pane is back to a fixed `420px`, which matches the saved legacy file structure.

## 2026-03-20 20:53 - Extend only detail viewport to page edge

- Kept the saved legacy shell proportions intact (`main = flex-1`, detail slot = `420px`) and limited the new change to the detail panel only.
- Wrapped the detail content in a dedicated fixed viewport layer so the visual panel extends from the old detail left edge all the way to the right edge of the browser.
- Preserved the inner content width at `420px` to avoid changing the reading layout itself, while moving the actual scrollbar to the far-right viewport edge.
- Verified locally and on the live site that `mainWidth` stays `892`, the original detail slot stays `420`, the rendered detail viewport expands to `580` on a `1920px` screen, and `panelRightGap = 0`.

## 2026-03-20 21:01 - Remove `Mail body` label from detail pane

- Removed the extra English heading `Mail body` from the email content section in the detail pane.
- Kept the Vietnamese section kicker `Nội dung email` and left the rest of the detail layout unchanged.
- Rebuilt and redeployed the live app so the label disappears immediately after refresh.

## 2026-03-20 21:11 - Pin detail reply actions to footer and jump into composer

- Reworked the detail pane into a two-part shell: a scrollable content region and a fixed footer action bar for `Trả lời` / `Chuyển tiếp`.
- Moved the active composer to the top of the detail flow so reply/forward mode becomes the primary context instead of appearing below the original email body.
- Added automatic scroll-to-top plus input focus when opening the composer, so clicking `Trả lời` from the footer immediately lands the user in the reply form.
- Verified on the live app with a long `Undeliverable` email that the footer stays fixed while only the detail content scrolls, and that reply mode resets `scrollTop` to `0` with the composer visible near the top of the panel.

## 2026-03-20 21:23 - Enable real SMTP send for reply/forward composer

- Confirmed on the VPS that SMTP auth succeeds against `mail.congmail.top` with both `STARTTLS 587` and `SSL 465`, reusing the central mailbox credential already present for IMAP.
- Added backend SMTP config defaults/fallbacks plus a new `backend/app/mailer.py` service to send composed messages with `To`, `CC`, `Subject`, `Body`, and reply threading headers when available.
- Added `POST /api/messages/{message_id}/send` and connected the frontend composer send button to that API, including loading state, success toast, and composer close-on-success.
- Fixed a real delivery issue by adding the missing `Date` header after the first smoke test was rejected by the mail content filter as `BAD HEADER`.
- Verified end-to-end on the live app: forwarded a real email to alias `codexsend1774016575967@congmail.top`, saw `Đã gửi chuyển tiếp`, and confirmed the forwarded message appeared back in the inbox on the first refresh cycle.

## 2026-03-20 21:40 - Flatten composer visuals and split send-button styles

- Kept the composer logic and SMTP send flow intact, but separated the visual treatment of the send buttons by mode.
- Changed `Gửi chuyển tiếp` to a white button with a light neutral border, while keeping `Gửi trả lời` on the existing orange primary style.
- Removed the orange-tinted composer surface and switched the form fields to a flatter white treatment with a soft neutral border and no orange glow on focus.
- Redeployed only the updated frontend files to VPS and verified live that forward is white, reply remains orange, the composer background is flat white, and the textarea/input outline no longer looks blurry.

## 2026-03-20 21:48 - Add keyboard Delete shortcut for selected email

- Added a global `keydown` handler in the frontend so pressing `Delete` removes the currently selected email row through the same delete flow used by the hover trash icon.
- Guarded the shortcut so it does nothing while focus is inside `input`, `textarea`, `select`, or editable content, avoiding accidental deletes during reply/forward editing.
- Redeployed the updated `app.js` to VPS and verified live that selecting a row then pressing `Delete` opens the existing confirm dialog `Xóa email này khỏi dashboard?`.

## 2026-03-20 21:58 - Add page-scoped multi-select like desktop file lists

- Extended inbox row selection to support `Ctrl/Cmd + click` toggle, `Shift + click` range selection, and `Ctrl/Cmd + A` to select all rows on the current paginated inbox page.
- Unified row-trash delete and keyboard `Delete` into the same batch delete flow, so multiple selected emails now confirm once with a count-aware message before removal.
- Added click-outside clearing for multi-select mode: clicking anywhere outside inbox rows now drops the selection and resets the detail pane instead of leaving stale batch state behind.
- Verified live that `Ctrl + click` selected 2 rows, `Shift + click` expanded the range to 3 rows, `Ctrl + A` selected all 12 visible rows on the page, `Delete` opened the batch confirm dialog, and clicking outside reduced the selection back to `0`.

## 2026-03-20 22:04 - Prevent text highlight during Shift range select

- Added `user-select: none` to inbox rows so mail list text no longer gets highlighted during desktop-style multi-select gestures.
- Added a `mousedown` guard for row interactions when `Shift`, `Ctrl`, or `Cmd` is held, preventing the browser's native text-selection behavior before the range-toggle logic runs.
- Redeployed the updated frontend and verified live that `Shift + click` still selects 4 rows correctly while `window.getSelection()` stays empty.

## 2026-03-20 22:10 - Add email translation endpoint

- Added `POST /api/messages/{message_id}/translate` in `backend/app/main.py` for auto-detect -> `vi` translation of subject and body.
- Added `backend/app/translator.py` to call the Google Translate web endpoint with `httpx` and shape a frontend-friendly payload.
- Chose not to add a new dependency or schema/config change; translation now runs as a lightweight on-demand backend helper.
- Verified the new backend files with `py_compile` and a local smoke test that mocked the translation response shape.

## 2026-03-20 22:18 - Add in-panel Google-style translate action for email detail

- Added an icon-only translate action at the far right of the detail meta row so subject/body can be translated in place without leaving the reader panel.
- Wired the detail pane to call the new translation endpoint on demand, cache the translated subject/body per message, and toggle between translated Vietnamese content and the original email.
- Styled the translate control with a Google-inspired multicolor ring, loading spinner state, and a small translation status chip under the subject for better readability.
- Verified local translation logic with `py_compile`, `node --check`, and a live backend smoke test that returned `source_language = en`, `target_language = vi`, plus translated subject/body.

## 2026-03-20 22:27 - Sync current project state to GitHub

- Reviewed the git worktree, confirmed the active branch is `main`, and kept runtime-only files like `run.err` / `run.log` out of the commit.
- Prepared a single source-control sync for the current live/local state so GitHub matches the deployed inbox, composer, multi-select, and translation features.
- Proceeded to stage, commit, and push the tracked application/backend/docs files to `origin/main`.
