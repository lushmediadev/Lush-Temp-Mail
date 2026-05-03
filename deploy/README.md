# Lush Temp Mail VPS Deploy

## 1. Copy repo to VPS

```bash
sudo mkdir -p /opt/lush-temp-mail
sudo chown -R deploy:deploy /opt/lush-temp-mail
git clone https://github.com/<your-org>/Lush-Temp-Mail.git /opt/lush-temp-mail/app
```

## 2. Prepare env

```bash
cd /opt/lush-temp-mail/app/deploy
cp .env.example .env
```

Set real values for:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `USER_USERNAME`
- `USER_PASSWORD`
- `IMAP_PASSWORD`
- `SMTP_PASSWORD` if it is different from the IMAP password

For the current live stack, keep:

- `IMAP_HOST=mx.lushmedia.net`
- `IMAP_PORT=993`
- `SMTP_HOST=mx.lushmedia.net`
- `SMTP_PORT=587`
- `SMTP_SECURITY=starttls`
- `MAIL_SYNC_INTERVAL_S=4`
- `MAIL_IDLE_ENABLED=true`
- `MAIL_IDLE_TIMEOUT_S=1500`
- `DEFAULT_ALIAS_HOURS=0` to keep aliases active until manually expired or deleted
- `MESSAGE_RETENTION_DAYS=0` to keep messages until manually deleted

This app reads IMAP over the mail domain's real TLS endpoint. Do not switch back to
`host.docker.internal`, because the temp-mail container is no longer relying on the
host-gateway path for mail access.

The recommended runtime mode is:

- background `IMAP IDLE` enabled for near-realtime mailbox updates
- `MAIL_SYNC_INTERVAL_S` kept as the fallback polling delay if `IDLE` drops or is unsupported
- admin UI polling only the app database, not forcing a full IMAP sync on every refresh tick

By default the reply/forward composer can reuse the same central mailbox credentials:

- `SMTP_USERNAME=contact@lushmedia.net`
- `SMTP_PASSWORD=<same as IMAP_PASSWORD>`
- `SMTP_FROM_ADDRESS=contact@lushmedia.net`
- `SMTP_FROM_NAME=LushMail`

## 3. Install helper

```bash
cd /opt/lush-temp-mail/app/deploy
sudo ./scripts/install_helpers.sh
```

## 4. Start app

```bash
cd /opt/lush-temp-mail/app/deploy
docker compose --env-file .env -f docker-compose.vps.yml up -d --build
```

Login flow after deploy:

- username `admin` goes to the admin dashboard at `/`
- username `user` goes to the user inbox UI at `/user.html`
- the logout button on either flow clears the same session cookie and returns to `/`

## 4a. Change admin login later

```bash
lushtempmail set-admin --username adminmoi --password 'MatKhauMoi123'
```

If you do not pass `--password`, the script will prompt securely.

## 4b. Change user login later

```bash
lushtempmail set-user --username usermoi --password 'MatKhauUser123'
```

If you do not pass `--password`, the script will prompt securely.

## 5. Caddy

Add the snippet from `deploy/Caddyfile.snippet` into the VPS Caddy config that currently owns `80/443`.

Recommended setup on this VPS:

- connect this app to the external Docker network `shared_proxy`
- connect this app to the external Docker network `mailstack_default`
- let Caddy reverse proxy directly to `lushtempmail-app:8010`
- do not publish the temp-mail app on a public host port
- keep `IMAP_HOST=mx.lushmedia.net`, because the mailserver container exposes that DNS alias on `mailstack_default`

## 6. Mail prerequisite

To support direct addresses like `abc123@lushmedia.net` without pre-creating aliases, the mail stack must enable a catch-all rule that forwards `@lushmedia.net` into `contact@lushmedia.net`. This app only consumes the central inbox via IMAP and auto-discovers aliases from inbound mail.

Recommended DNS for inbound temp mail:

- `A mx 109.123.227.253` (`DNS only`)
- `MX @ 10 mx.lushmedia.net` (`DNS only`)
- `TXT @ v=spf1 mx a -all`
- `TXT _dmarc v=DMARC1; p=none; rua=mailto:dmarc@lushmedia.net; pct=100`
