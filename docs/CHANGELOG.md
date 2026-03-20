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

### 2026-03-20 18:22 - clone_repo_and_run_local_app
- Added: local clone at `C:\Users\PC\Lush-Temp-Mail` and local Python virtual environment `.venv`.
- Changed: installed runtime dependencies and launched the app locally on `127.0.0.1:8010`.
- Fixed: verified the local startup path with a passing `/api/health` response before opening the UI.
- Affected files: `.venv/`, `run.log`, `run.err`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; the app is available locally now, but IMAP sync stays idle until a real `IMAP_PASSWORD` is configured.

### 2026-03-20 18:48 - simplify_local_inbox_layout_for_review
- Added: footer pagination controls for the inbox list area.
- Changed: removed the hero cover, tightened the layout under the topbar, and reduced the sidebar to inbox filters only.
- Fixed: made the mail list scroll independently so navigation and detail panel remain stable during browsing.
- Affected files: `index.html`, `style.css`, `app.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; local frontend flow is intentionally simplified and no longer exposes alias management in the UI.

### 2026-03-20 18:57 - trim_topbar_and_add_warm_favicon
- Added: `favicon.svg` for the browser tab with a warm red mail-style icon.
- Changed: removed the sidebar info card plus the topbar sync control and admin identity cluster.
- Fixed: top-level chrome is now visually cleaner for the inbox-focused layout review.
- Affected files: `index.html`, `style.css`, `app.js`, `favicon.svg`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; purely presentational local UI cleanup.

### 2026-03-20 19:00 - redesign_favicon_with_lucide_like_mail_mark
- Changed: favicon now uses a simpler lucide-style mail icon with bolder strokes.
- Fixed: improved readability of the tab icon at very small sizes.
- Affected files: `favicon.svg`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; favicon-only visual refinement.

### 2026-03-20 19:04 - switch_favicon_to_app_logo_mark
- Changed: browser favicon now points to `logo.svg` so the tab uses the same icon mark as the header.
- Fixed: removed the mismatch between header branding and tab branding during local review.
- Affected files: `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; favicon source swap only.

### 2026-03-20 19:14 - deploy_latest_ui_polish_to_vps
- Changed: synced the latest local inbox-focused UI files to the live VPS app copy.
- Fixed: public `lush.congmail.top` now serves the updated simplified layout after redeploy.
- Affected files: `index.html`, `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; live container was rebuilt and restarted successfully during the deploy.

### 2026-03-20 19:35 - inbox_interaction_polish_and_faster_sync
- Added: message delete API plus UI hover delete action, and automatic 7-day message cleanup during sync.
- Changed: inbox rows now render alias first, sender second, subject third, with deterministic random avatar colors and alias-aware search.
- Fixed: live inbox refresh is now more responsive via faster frontend polling and `MAIL_SYNC_INTERVAL_S=4` on the VPS runtime.
- Affected files: `app.js`, `style.css`, `index.html`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/imap_sync.py`, `backend/app/utils.py`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; runtime behavior for inbox refresh and message retention changed on live.

### 2026-03-20 20:17 - important_group_retention_60d_and_composer_polish
- Added: `Quan trọng` inbox group, message star toggle API/state, and reply/forward composer UI with `CC` inside the detail panel.
- Changed: alias default lifetime is now `60 ngày`, message auto-cleanup is now `60 ngày`, and row actions use icon-only styling consistent with the app icon language.
- Fixed: important messages can now be pinned and filtered cleanly, while the live UI preserves alias-first ordering and faster inbox review flow.
- Affected files: `AGENTS.md`, `index.html`, `app.js`, `style.css`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/imap_sync.py`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; DB schema now auto-adds `important`, and live retention/runtime defaults changed from 7 days to 60 days.

### 2026-03-20 20:36 - detail_pane_layout_and_recent_badge_stability
- Added: bottom action bar for `Trả lời` / `Chuyển tiếp` and a wider reader-shell layout in the desktop email detail pane.
- Changed: removed the old top `Email actions` card, widened the right reading column to fill remaining space, and kept the compose draft inline above the new footer actions.
- Fixed: switching between groups no longer reflags old emails as `Email mới`, and unchanged inbox lists no longer re-render every auto-refresh cycle, eliminating the visible hover flicker.
- Affected files: `index.html`, `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low to medium; frontend-only change, but the desktop reading layout and refresh behavior are noticeably different.

### 2026-03-20 20:40 - viewport_edge_detail_pane
- Changed: the app shell now uses the full viewport width, the inbox list is flexible again, and the desktop detail pane is anchored to the far right with responsive fixed width.
- Fixed: the message detail scrollbar now sits at the right page edge instead of inside a centered shell, so widening the reader no longer compresses the inbox list unnaturally.
- Affected files: `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend layout-only adjustment for large-screen desktop view.

### 2026-03-20 20:44 - revert_to_centered_reference_layout
- Changed: reverted the last desktop shell change and restored the centered `max-width` layout to match the user's reference image.
- Fixed: inbox list and detail pane proportions are back to the previous centered-shell balance instead of the viewport-edge layout.
- Affected files: `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; layout-only revert on desktop.

### 2026-03-20 20:48 - match_saved_legacy_layout_file
- Changed: aligned the desktop shell with the user's saved HTML reference, using `main` as `flex-1` and a fixed `420px` detail pane inside the centered `1600px` shell.
- Fixed: the live layout now matches the saved legacy structure instead of the intermediate proportional variants inferred from screenshots.
- Affected files: `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; desktop layout-only adjustment.

### 2026-03-20 20:53 - detail_viewport_edge_without_layout_shift
- Changed: only the desktop detail panel viewport now extends to the right page edge, while the original `420px` layout slot and inbox column widths stay unchanged.
- Fixed: the detail scrollbar now sits flush with the browser edge without altering the surrounding shell proportions or compressing the email list.
- Affected files: `index.html`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; desktop detail-pane rendering only.

### 2026-03-20 21:01 - remove_mail_body_label
- Changed: removed the `Mail body` heading from the detail content section.
- Affected files: `app.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; text-only UI cleanup in the detail pane.

### 2026-03-20 21:11 - sticky_detail_footer_and_compose_jump
- Changed: the detail pane now has a fixed footer action bar, while the content area scrolls independently above it.
- Changed: opening `Trả lời` / `Chuyển tiếp` now renders the composer at the top of the detail flow instead of below the email body.
- Fixed: clicking reply from the footer no longer requires manual scrolling back up to find the composer form.
- Affected files: `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; detail-pane interaction model changed, but only within the right reading panel.

### 2026-03-20 21:23 - real_smtp_send_for_reply_forward
- Added: SMTP sending service, send API endpoint, and frontend send integration for reply/forward with `CC`.
- Changed: deploy config now documents `SMTP_*` settings and defaults them to the same central mailbox used by IMAP when appropriate.
- Fixed: real outgoing messages now include the required `Date` header, avoiding the previous `BAD HEADER` rejection from the mail filter.
- Affected files: `app.js`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/mailer.py`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; composer send buttons now perform real SMTP delivery from `contact@congmail.top`.

### 2026-03-20 21:40 - flatten_composer_visuals_and_split_send_button_styles
- Added: mode-specific send-button styling so reply and forward can use different visual weight without changing behavior.
- Changed: the composer panel now uses a flat white surface, and form fields use softer neutral borders instead of the orange-tinted look.
- Fixed: `Gửi chuyển tiếp` is now white, `Gửi trả lời` remains orange, and the textarea/input outline no longer shows the blurry orange focus treatment from before.
- Affected files: `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend-only visual polish inside the detail composer.

### 2026-03-20 21:58 - page_scoped_multi_select_and_batch_delete
- Added: `Ctrl/Cmd + click`, `Shift + click`, and `Ctrl/Cmd + A` multi-select support for inbox rows on the current page, plus click-outside to clear batch selection.
- Changed: delete actions now reuse a shared batch delete flow so row-trash and keyboard `Delete` can remove one or many selected emails with the same confirmation logic.
- Fixed: bulk selection behaves more like a desktop file list, and stale multi-select state no longer sticks around after you click away from the inbox rows.
- Affected files: `app.js`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; inbox row interaction model changed, but the scope is intentionally limited to the currently visible paginated page.

### 2026-03-20 22:04 - prevent_text_highlight_during_shift_range_select
- Changed: inbox rows now explicitly disable text selection during pointer interaction.
- Fixed: `Shift + click` range selection no longer highlights sender/subject text while still preserving the multi-select behavior.
- Affected files: `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend-only interaction polish for inbox row selection.

### 2026-03-20 22:10 - translate_message_endpoint_auto_detect_vi
- Added: `POST /api/messages/{message_id}/translate` plus `backend/app/translator.py` for on-demand message translation.
- Changed: subject/body translation now uses auto-detect -> `vi` without adding a new dependency or schema change.
- Fixed: frontend now has a clear translation payload shape with separate `subject` and `body` results plus detected source language.
- Affected files: `backend/app/main.py`, `backend/app/translator.py`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; translation depends on an external Google Translate web endpoint, but runtime impact is isolated to the new route.

### 2026-03-20 22:18 - in_panel_google_style_translate_action
- Added: a Google-style translate icon button in the email detail header that translates `subject` and `body` in place.
- Changed: translated content is now cached per message in the frontend and can be toggled against the original email without extra layout shifts.
- Fixed: admins can translate foreign-language emails directly inside the detail pane with default auto-detect -> Vietnamese behavior.
- Affected files: `app.js`, `style.css`, `backend/app/main.py`, `backend/app/translator.py`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; the new UI depends on the backend translation helper and an external Google Translate web endpoint.

### 2026-03-20 22:27 - sync_current_state_to_github
- Changed: the full current tracked project state was prepared for source-control sync on `origin/main`.
- Added: fresh docs entries describing the GitHub sync task itself for parity with the local project memory.
- Affected files: `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; source-control sync only, with runtime log files intentionally left out of the commit.
