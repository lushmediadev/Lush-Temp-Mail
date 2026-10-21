# LushMedia full mail migration

This migration includes the web app and the `lushmedia.net` mail domain. The helper `scripts/migrate_vps.sh` only copies the app `.env` and SQLite data; it does not move a mailserver or mailbox data.

## Confirm the source

Before moving data, confirm the active origin from DNS and service responses. Do not assume the old app VPS is also the active mailserver. Current public checks identify `109.123.227.253` for both the app health endpoint and SMTP greeting; SSH access to this host is required to preserve its live mailbox and application data.

## Back up first

Before changing the target Docker Mailserver, make a root-only backup of its existing compose file, mailserver configuration, mail data, and mail state. Back up the source app database, environment, mail configuration, and mail data. Record checksums and run SQLite `PRAGMA quick_check` on copied databases.

Do not copy the entire shared mailserver volume blindly. Map only the `lushmedia.net` account and messages into the target so mailboxes for other domains remain separate. Preserve the target `temp.darkambient.co` account, aliases, DKIM, certificates, and mail data.

## Prepare target services

1. Deploy the LushMail app with `docker-compose.nginx.yml`; it uses `127.0.0.1:8017` and the existing `darkambient_mail` Docker network.
2. Add `contact@lushmedia.net` and the LushMedia catch-all/postmaster/DMARC aliases to the existing Docker Mailserver without replacing its current accounts.
3. Add `mx.lushmedia.net` as a Docker DNS alias for the mailserver and issue a mail TLS certificate that includes both the current DarkAmbient MX hostname and `mx.lushmedia.net`. The existing source Caddy can forward HTTP ACME challenges to the target before the DNS change.
4. Publish authenticated SMTP submission on `587` and IMAPS on `993` (optionally SMTPS on `465`). Do not enable an open relay.
5. Set the app's IMAP/SMTP host to `mx.lushmedia.net` and central mailbox to `contact@lushmedia.net`.
6. Reuse the source's existing `mail` DKIM key and published selector in the target's Rspamd `dkim_signing.conf`; keep the DarkAmbient signing entry intact.

## Cut over and verify

After target health and account checks pass, update DNS:

- `A mail.lushmedia.net -> 194.233.69.135` (proxied for HTTPS)
- `A mx.lushmedia.net -> 194.233.69.135` (DNS only)
- `MX lushmedia.net 10 mx.lushmedia.net` (DNS only)

Preserve existing SPF, DKIM, and DMARC records. Verify public `/api/health`, protected login, IMAP sync, authenticated SMTP submission, inbound delivery to a new alias, and SPF/DKIM/DMARC `Authentication-Results` from an external mailbox. Keep the source running until those checks pass and rollback is no longer needed.

For mail that arrives at the old IP during DNS propagation, run `scripts/sync_source_maildir.py` on the target through `lushmedia-mail-bridge.timer`. Its ledger prevents repeated copies when a source Maildir message moves between `new/` and `cur/`. Remove this timer and the temporary source SSH authorization after the rollback window.
