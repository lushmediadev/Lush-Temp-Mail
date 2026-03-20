# Changelog

### 2026-03-20 16:35 - rule_bootstrap
- Added: root `AGENTS.md` for `D:\Lush-Temp-Mail`.
- Added: project memory docs under `D:\Lush-Temp-Mail\docs\`.
- Changed: documented current static-only state and target temp-mail backend direction.
- Fixed: missing project rules/context baseline before implementation.
- Affected files: `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; documentation/bootstrap only, no runtime behavior changed.

### 2026-03-20 17:20 - temp_mail_backend_and_vps_runtime
- Added: FastAPI backend, SQLite persistence, IMAP sync service, parser tests, Dockerfile, requirements, deploy assets, backend/deploy AGENTS files.
- Changed: root frontend now uses real API/session state instead of mock email data.
- Fixed: implemented catch-all-based alias auto-discovery so arbitrary `@congmail.top` addresses can appear without manual pre-creation.
- Affected files: `index.html`, `app.js`, `style.css`, `.gitignore`, `requirements.txt`, `Dockerfile`, `backend/**`, `deploy/**`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; app/runtime behavior changed significantly, public DNS for `lush.congmail.top` still pending before final public HTTPS cutover.

### 2026-03-20 17:32 - public_proxy_fix
- Added: documented Docker host-gateway requirement for shared Caddy.
- Changed: reverse proxy target for `lush.congmail.top` from `127.0.0.1:8012` to `host.docker.internal:8012`.
- Fixed: resolved public `502` cause where Caddy container could not reach the temp-mail app bound on the host loopback.
- Affected files: `deploy/Caddyfile.snippet`, `deploy/README.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; requires syncing the same proxy fix to the live VPS Caddy stack.

### 2026-03-20 17:36 - shared_proxy_network_fix
- Added: `shared_proxy` network attachment and explicit alias `lushtempmail-app` for the temp-mail app service.
- Changed: Caddy upstream for `lush.congmail.top` now points to `lushtempmail-app:8010`.
- Fixed: removed dependency on host loopback publishing, which still blocked Caddy from reaching the app across containers.
- Affected files: `deploy/docker-compose.vps.yml`, `deploy/Caddyfile.snippet`, `deploy/README.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; live VPS compose and Caddy config must be synced together.

### 2026-03-20 17:46 - admin_credential_helper
- Added: `deploy/scripts/set_admin_credentials.sh` for changing temp-mail admin credentials on VPS.
- Changed: `lushtempmail` helper now supports `set-admin`.
- Fixed: removed the need to manually edit `deploy/.env` when rotating temp-mail admin login.
- Affected files: `deploy/scripts/set_admin_credentials.sh`, `deploy/scripts/install_helpers.sh`, `deploy/scripts/lushtempmail.sh`, `deploy/README.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; operational helper only, verified on VPS.

### 2026-03-20 16:55 - imap_live_sync_recovery
- Added: external Docker network attachment `mailstack_default` for the temp-mail app service.
- Changed: deploy defaults/documentation now keep `IMAP_HOST=mail.congmail.top` instead of the broken host-gateway route.
- Fixed: live inbox sync for catch-all addresses such as `hoang123@congmail.top`.
- Affected files: `deploy/docker-compose.vps.yml`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; deploy topology changed slightly, but the public `lush.congmail.top` route is unchanged and IMAP sync is now stable.

### 2026-03-20 17:03 - auto_refresh_and_relative_time_ticker
- Added: frontend auto-refresh loop and separate relative-time ticker while the admin page is visible.
- Changed: recommended/live `MAIL_SYNC_INTERVAL_S` from 20 to 10 seconds for quicker inbox import.
- Fixed: mail list and relative time labels no longer require manual refresh to update.
- Affected files: `app.js`, `deploy/.env.example`, `deploy/README.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; browser may need a hard refresh to fetch the new frontend bundle from cache.

### 2026-03-20 17:18 - new_mail_emphasis_and_flicker_removal
- Added: `Email mới` badge and stronger highlight state for newly arrived messages in `Mail feed`.
- Changed: silent auto-refresh now triggers real sync every 8 seconds, while relative-time labels refresh in place every 10 seconds.
- Fixed: open message detail no longer disappears/reappears during background refresh.
- Affected files: `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; the browser may still need a hard refresh once to fetch the latest frontend assets.

### 2026-03-20 17:28 - tone_down_new_mail_styling
- Changed: removed the bright row highlight and pulse animation from new-mail styling.
- Fixed: message rows are back to the original neutral look while keeping the `Email mới` badge.
- Affected files: `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; browser may need a hard refresh to fetch the updated stylesheet.

### 2026-03-20 17:35 - publish_repo_to_github
- Added: git publishing step for `D:\Lush-Temp-Mail` to the empty GitHub repository `shinemusicllc/Lush-Temp-Mail`.
- Changed: local folder becomes the canonical git repo for future commits and pushes.
- Fixed: project is no longer only a filesystem copy; future VPS updates can track GitHub properly.
- Affected files: `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; assumes current local state is the desired initial upstream snapshot.
