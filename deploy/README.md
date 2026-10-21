# Lush Temp Mail VPS Deploy

## Canonical production layout

- Web app: `https://mail.lushmedia.net`
- Email addresses: `@lushmedia.net`
- SMTP/IMAP host: `mx.lushmedia.net` (DNS only)
- Central mailbox: `contact@lushmedia.net`
- Production VPS: `194.233.69.135`, SSH alias `lush1-vps`
- The VPS already runs `temp.darkambient.co`. LushMail uses a separate app container, data directory, and login rate-limit zone while joining the existing `darkambient_mail` network for IMAP/SMTP.

Do not route SMTP/IMAP through the proxied web hostname. Keep the existing DarkAmbient mailbox, DKIM, certificates, and app data intact while adding the LushMedia domain.

## 1. Install the app

```bash
sudo mkdir -p /opt/lush-temp-mail
sudo chown -R deploy:deploy /opt/lush-temp-mail
git clone https://github.com/lushmediadev/Lush-Temp-Mail.git /opt/lush-temp-mail/app
```

## 2. Configure the app

```bash
cd /opt/lush-temp-mail/app/deploy
cp .env.example .env
```

Set unique values for `ADMIN_PASSWORD`, `USER_PASSWORD`, and `IMAP_PASSWORD`. The real `contact@lushmedia.net` password must match the account on the mailserver. Keep secrets in this VPS file only.

The app settings should use:

- `APP_BASE_URL=https://mail.lushmedia.net`
- `TEMPMAIL_PUBLIC_DOMAIN=mail.lushmedia.net`
- `TEMPMAIL_MAIL_DOMAIN=lushmedia.net`
- `IMAP_HOST=mx.lushmedia.net`, port `993`
- `SMTP_HOST=mx.lushmedia.net`, port `587`, `SMTP_SECURITY=starttls`
- `IMAP_USERNAME=contact@lushmedia.net`
- `SMTP_USERNAME=contact@lushmedia.net`
- `CENTRAL_MAILBOX=contact@lushmedia.net`

The mailserver container on `darkambient_mail` must have the Docker network alias `mx.lushmedia.net`, and its TLS certificate must include that name. This lets the app use the canonical mail hostname internally while resolving to the mailserver container.

Keep `MAIL_SYNC_INTERVAL_S=4`, `MAIL_IDLE_ENABLED=true`, `MAIL_IDLE_TIMEOUT_S=1500`, and the current retention settings unless there is a separate product decision.

## 3. Start the app

```bash
cd /opt/lush-temp-mail/app
docker compose -f deploy/docker-compose.nginx.yml --env-file deploy/.env up -d --build
```

The container binds only to `127.0.0.1:8017`; host Nginx serves public HTTP/HTTPS.

## 4. Configure Nginx and TLS

Before DNS cutover, install `deploy/nginx/lushmedia-acme-precutover.conf` on the target. The old Caddy instance temporarily forwards `/.well-known/acme-challenge/` for both LushMedia hostnames to the target's port 80. After issuing the certificates, replace the temporary Nginx vhost with `deploy/nginx/mail.lushmedia.net.conf`, run `nginx -t`, and reload Nginx. Remove the Caddy forwarding after DNS points to the target.

The mail certificate at `/etc/letsencrypt/live/mx.temp.darkambient.co-0001` includes both `mx.lushmedia.net` and `mx.temp.darkambient.co`. The web certificate is at `/etc/letsencrypt/live/mail.lushmedia.net`. Preserve Certbot renewal and the existing mailserver reload hook.

## 5. Add the LushMedia mail domain

Add `contact@lushmedia.net` to the existing Docker Mailserver without replacing DarkAmbient accounts. Add aliases for:

- `@lushmedia.net -> contact@lushmedia.net`
- `postmaster@lushmedia.net -> contact@lushmedia.net`
- `dmarc@lushmedia.net -> contact@lushmedia.net`

The target Rspamd signing config must include `lushmedia.net` and the source's existing `mail` DKIM private key, so the published DNS selector continues to work. Back up the mailserver config and mailbox data before changing the shared Docker Mailserver compose file. Publish SMTP submission on `587`, IMAPS on `993`, and SMTPS `465`; keep authenticated sending enabled and do not configure an open relay.

## 6. DNS

After the target is healthy and mail flow is verified:

- Set `A mail.lushmedia.net -> 194.233.69.135` as proxied for the web app.
- Set `A mx.lushmedia.net -> 194.233.69.135` as DNS only.
- Keep `MX lushmedia.net 10 mx.lushmedia.net` as DNS only.
- Preserve existing SPF/DMARC and the published `mail` DKIM selector. Confirm SPF, DKIM, and DMARC with a real external message.

During DNS propagation, the target's `lushmedia-mail-bridge.timer` runs `deploy/scripts/sync_source_maildir.py` every five minutes. It copies only new mail files from the old VPS and records copied message keys. Stop the timer and remove its temporary SSH key after late mail has stopped and the rollback window is closed.

## 7. Migration limitations

`deploy/scripts/migrate_vps.sh` moves the app checkout, `.env`, and SQLite data only. It does not migrate Docker Mailserver, mailbox contents, DKIM keys, Nginx, certificates, or DNS. For a complete mail migration, follow the active task runbook and preserve the source until external inbound/outbound checks pass.
