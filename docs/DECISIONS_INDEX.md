# Decisions Index

| ID | Decision | Status | Scope | Impact |
| --- | --- | --- | --- | --- |
| DEC-001 | Keep the app as FastAPI backend plus vanilla root HTML/CSS/JS; do not introduce a frontend bundler by default. | Active | app architecture | High |
| DEC-002 | User lookup must support aliases that were never pre-created because inbound mail can auto-discover recipients. | Active | mail flow | High |
| DEC-003 | Mobile user inbox uses a single page scroll for search/list and a separate full-screen reader overlay for message detail. | Active | user mobile UI | Medium |
| DEC-004 | Use `mail.lushmedia.net` for the web app and `mx.lushmedia.net` for SMTP/IMAP, with `lushmedia.net` as the recipient domain. | Active | domains and mail routing | High |
| DEC-005 | Share the existing target Docker Mailserver across LushMedia and DarkAmbient, with separate mailboxes and a temporary late-mail bridge during DNS cutover. | Active | VPS migration | High |

