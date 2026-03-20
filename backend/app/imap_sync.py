from __future__ import annotations

import imaplib
import logging
import threading
from email import message_from_bytes
from email.message import Message
from email.utils import getaddresses

from . import db
from .config import settings
from .parser import collect_headers, extract_links, extract_otps, extract_recipient, extract_snippet, extract_text_parts, parse_received_at
from .utils import iso_days_ago, utc_now_iso


logger = logging.getLogger("lush_temp_mail.sync")


class MailSyncService:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if not settings.sync_enabled:
            logger.info("Mail sync disabled by config")
            return
        if not settings.imap_password:
            logger.warning("IMAP password missing; mail sync will stay idle")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="mail-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                synced = self.sync_once()
                if synced:
                    logger.info("Mail sync imported %s message(s)", synced)
            except Exception as exc:
                logger.exception("Mail sync failed: %s", exc)
            self._stop_event.wait(settings.sync_interval_s)

    def sync_once(self) -> int:
        db.cleanup_expired_aliases(utc_now_iso())
        db.cleanup_old_messages(iso_days_ago(settings.message_retention_days))
        if not settings.sync_enabled or not settings.imap_password:
            return 0

        last_uid = int(db.get_state("imap_last_uid", "0") or "0")
        synced = 0

        with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
            client.login(settings.imap_username, settings.imap_password)
            client.select("INBOX")
            search_criteria = "ALL" if last_uid == 0 else f"UID {last_uid + 1}:*"
            status, data = client.uid("search", None, search_criteria)
            if status != "OK" or not data or not data[0]:
                return 0

            uids = [int(value) for value in data[0].split() if value]
            for uid in uids:
                status, fetched = client.uid("fetch", str(uid), "(RFC822)")
                if status != "OK" or not fetched or not fetched[0]:
                    continue
                raw_message = fetched[0][1]
                message = message_from_bytes(raw_message)
                payload = self._parse_message(uid, message)
                db.set_state("imap_last_uid", str(uid))
                if payload is None:
                    continue
                stored = db.store_message(payload)
                if stored is not None:
                    synced += 1

        return synced

    def _parse_message(self, uid: int, message: Message) -> dict | None:
        recipient = extract_recipient(message, settings.mail_domain, settings.central_mailbox)
        if not recipient:
            return None

        sender_name = ""
        sender_email = ""
        sender_candidates = getaddresses(message.get_all("From", []))
        if sender_candidates:
            sender_name, sender_email = sender_candidates[0]

        text_body, html_body = extract_text_parts(message)
        return {
            "imap_uid": uid,
            "message_id": message.get("Message-Id", ""),
            "recipient_address": recipient,
            "from_name": sender_name or sender_email or "Unknown Sender",
            "from_email": sender_email,
            "subject": message.get("Subject", "(No subject)"),
            "snippet": extract_snippet(text_body),
            "text_body": text_body,
            "html_body": html_body,
            "extracted_links": extract_links(text_body, html_body),
            "extracted_otps": extract_otps(text_body, html_body),
            "raw_headers": collect_headers(message),
            "received_at": parse_received_at(message),
        }
