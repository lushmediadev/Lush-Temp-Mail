# Project Context

- Product: `Lush-Temp-Mail`, a FastAPI + SQLite temp-mail app with admin and user inbox flows.
- Public app URL: `https://mail.lushmedia.net`.
- Recipient domain: `lushmedia.net`; arbitrary aliases must continue to work without pre-creation.
- Mail transport host: `mx.lushmedia.net`; central mailbox: `contact@lushmedia.net`; incoming `@lushmedia.net` mail must route to that mailbox.
- Prepared production host: VPS `194.233.69.135`, available through SSH alias `lush1-vps`. It runs `temp.darkambient.co` and a separate LushMail app on `127.0.0.1:8017`; both mail domains share the existing Docker Mailserver.
- Current public app and MX DNS still route to the source `109.123.227.253`. The VPS `82.197.71.6` is a separate legacy deployment, not the live LushMedia source.
- Source and target backups are at `/root/lushmail-migration-20261021` on their respective VPS hosts. The target has the mailbox, SQLite database, LushMedia account/aliases, DKIM key, and TLS certificates. A five-minute bridge copies late mail from the source while DNS changes propagate.
- Cloudflare DNS cutover is pending account sign-in. Keep the source service available until public web and external mail flow are verified.
- Deployment should use the target's existing Nginx reverse proxy and a dedicated loopback app port; do not bind another service to public `80/443`.
