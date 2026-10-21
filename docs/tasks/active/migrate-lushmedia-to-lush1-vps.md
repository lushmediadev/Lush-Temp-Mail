# Migrate LushMedia mail to lush1-vps

## Goal

Move the `mail.lushmedia.net` web app and `lushmedia.net` mail service to VPS `194.233.69.135` while preserving the existing `temp.darkambient.co` service and LushMedia mailbox history.

## Canonical names

- Web app: `https://mail.lushmedia.net`
- Mail transport: `mx.lushmedia.net`
- Mail domain: `lushmedia.net`
- Central mailbox and catch-all target: `contact@lushmedia.net`

## Findings

- `mail.lushmedia.net/api/health` succeeds both through public DNS and when connected directly to `109.123.227.253`.
- `mx.lushmedia.net` resolves to `109.123.227.253`; its SMTP greeting is `mx.lushmedia.net`.
- Source SSH access was obtained with the credential provided by the user. A temporary target-to-source key is used only for transfer and late-mail sync.
- The provided source VPS `82.197.71.6` runs a legacy app and a shared mailserver for another domain. Its Lush Temp Mail database primarily contains that other domain's aliases, so it is not a safe substitute source for the live LushMedia mailbox.
- Target VPS `194.233.69.135` runs the DarkAmbient app and Docker Mailserver. The shared mailserver now publishes ports 25, 143, 465, 587, and 993; its certificate covers both `mx.temp.darkambient.co` and `mx.lushmedia.net`.

## Completed on 2026-10-21

- Backed up source SQLite with `quick_check=ok`, maildir, mail account/alias configuration, DKIM key, app environment, and web certificates. Backed up the target DarkAmbient mail stack and Nginx configuration before changing them.
- Imported 705 INBOX messages and the source SQLite database. Added the LushMedia account/catch-all and reused its published `mail` DKIM selector in Rspamd, while retaining the DarkAmbient domain.
- Issued certificates on the target before DNS cutover by forwarding ACME HTTP challenges from the source. Both the web certificate and dual-host mail certificate are valid through 2027-01-19.
- Started `lushmail-app` and Nginx on the target. Direct HTTPS `/api/health` returned 200; IMAP and SMTP STARTTLS authentication succeeded. A delivery to an uncreated alias was indexed with OTP and link extraction, and the outgoing message carried a LushMedia DKIM signature.
- Installed `lushmedia-mail-bridge.timer` on the target to import late Maildir messages from the source every five minutes. Its first run found no new mail.
- Checked that sample passwords in `.env` fail on both source and target because login users are stored in SQLite; the original account database is preserved. A login with an actual user password remains to be verified.

## Migration sequence

1. Obtain SSH access to the live source at `109.123.227.253` and verify its app/database/mailbox locations.
2. Back up the source app database, mail data, account/alias config, DNS settings, and target DarkAmbient mail stack.
3. Prepare an isolated LushMail app stack and add `lushmedia.net` to the target mailserver with the catch-all and DKIM records.
4. Transfer the LushMedia mailbox/app data, update app config to the canonical names above, and verify health, login, IMAP sync, SMTP authentication, and test delivery.
5. Cut over Cloudflare DNS and verify external inbound/outbound mail plus SPF/DKIM/DMARC.
6. Keep the source intact for rollback until the target is verified; only then retire the LushMedia-specific source service.

## Remaining cutover

Cloudflare is at the sign-in page. Once the DNS account is available, refresh the source SQLite snapshot just before cutover, point the proxied `mail` A and DNS-only `mx` A records to `194.233.69.135`, verify public web and external inbound/outbound mail, then keep the source/bridge during the rollback window. Remove the temporary SSH key, timer, and source service only after late deliveries have stopped.
