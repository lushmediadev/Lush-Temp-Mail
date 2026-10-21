## Deploy Rules

- Production target is `lush1-vps` (`194.233.69.135`), where host Nginx owns public ports `80/443`.
- The LushMail app uses `deploy/docker-compose.nginx.yml` and binds only `127.0.0.1:8017 -> container 8010`.
- The app joins external Docker network `darkambient_mail` to reach the shared mailserver. Keep the existing `temp.darkambient.co` app, database, mailbox, and hostname intact.
- SMTP/IMAP uses `mx.lushmedia.net`; the web app uses `mail.lushmedia.net`; recipient aliases use `@lushmedia.net`.
- Passwords and private keys stay only in VPS runtime files. Never commit them.

## Commands

- VPS compose: `cd /opt/lush-temp-mail/app/deploy && docker compose -f docker-compose.nginx.yml --env-file .env up -d --build`
- Helper usage: `lushtempmail status|logs|redeploy|update`
