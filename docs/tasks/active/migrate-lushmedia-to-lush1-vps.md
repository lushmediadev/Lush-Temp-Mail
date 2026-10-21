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
- Cut over Cloudflare `mail` (proxied) and `mx` (DNS only) A records to `194.233.69.135`. The MX record remains `mx.lushmedia.net` at priority 10. Both authoritative nameservers return the new MX address.
- Public `https://mail.lushmedia.net/api/health` returns 200 and the public page contains the updated `lushmedia.net` UI. Anonymous `/api/auth/session` returns 401. Public `temp.darkambient.co/api/health` remains 200.
- External SMTP connection to `mx.lushmedia.net:25` completed STARTTLS with a valid certificate and accepted an envelope recipient at `lushmedia.net` (no message DATA was sent). The mail bridge timer remains active and the source still has 6 users, 88 aliases, 760 messages, and 2 forwarding rules, matching the source snapshot counts.
- A real Gmail message sent to `20261021@lushmedia.net` was received by the target MX at 11:07:51 +07, delivered through the catch-all to `contact@lushmedia.net`, and indexed by the app. The app automatically created the inbound alias and the target database advanced to 762 messages/90 aliases. A short SMTP reply from the target to the same Gmail sender was accepted by Gmail MX with `250 2.0.0` at 11:09:26 +07.

## Migration sequence

1. Obtain SSH access to the live source at `109.123.227.253` and verify its app/database/mailbox locations.
2. Back up the source app database, mail data, account/alias config, DNS settings, and target DarkAmbient mail stack.
3. Prepare an isolated LushMail app stack and add `lushmedia.net` to the target mailserver with the catch-all and DKIM records.
4. Transfer the LushMedia mailbox/app data, update app config to the canonical names above, and verify health, login, IMAP sync, SMTP authentication, and test delivery.
5. Cut over Cloudflare DNS and verify external inbound/outbound mail plus SPF/DKIM/DMARC.
6. Keep the source intact for rollback until the target is verified; only then retire the LushMedia-specific source service.

## Remaining cutover

DNS, public web, real external inbound, and external SMTP submission are complete. The source remains intact for rollback, and the five-minute mail bridge handles late arrivals. A synthetic direct SMTP message from the old source was rejected at DATA as spam after that IP ceased to be authorized by SPF; it did not create a target message. The Gmail inbox placement and received SPF/DKIM/DMARC results require inspection in Gmail, and login with a current user password remains unverified. Remove the temporary SSH key, timer, and source service only after the rollback window and late deliveries have ended.
