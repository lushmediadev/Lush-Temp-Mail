from __future__ import annotations

import json
import sqlite3
from typing import Any

from .config import settings
from .parser import decode_mime_text, extract_links, extract_otps, html_to_text
from .translator import DEFAULT_TARGET_LANGUAGE, infer_language_hint, should_offer_translation
from .utils import iso_in_hours, normalize_address, split_address, utc_now_iso


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                local_part TEXT NOT NULL,
                domain TEXT NOT NULL,
                label TEXT,
                source TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                expires_at TEXT,
                last_message_at TEXT,
                last_sender TEXT,
                message_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imap_uid INTEGER NOT NULL UNIQUE,
                message_id TEXT,
                alias_id INTEGER,
                recipient_address TEXT NOT NULL,
                from_name TEXT,
                from_email TEXT,
                subject TEXT,
                snippet TEXT,
                text_body TEXT,
                html_body TEXT,
                attachments_json TEXT NOT NULL DEFAULT '[]',
                extracted_links_json TEXT NOT NULL DEFAULT '[]',
                extracted_otps_json TEXT NOT NULL DEFAULT '[]',
                raw_headers_json TEXT NOT NULL DEFAULT '{}',
                received_at TEXT NOT NULL,
                mailbox_received_at TEXT,
                ingested_at TEXT,
                unread INTEGER NOT NULL DEFAULT 1,
                suppressed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(alias_id) REFERENCES aliases(id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_recipient_received_at
            ON messages(recipient_address, received_at DESC);

            CREATE INDEX IF NOT EXISTS idx_messages_alias_received_at
            ON messages(alias_id, received_at DESC);
            """
        )
        message_columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
        if "important" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN important INTEGER NOT NULL DEFAULT 0")
        if "mailbox_received_at" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN mailbox_received_at TEXT")
        if "ingested_at" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN ingested_at TEXT")
        if "attachments_json" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN attachments_json TEXT NOT NULL DEFAULT '[]'")
        conn.execute("UPDATE messages SET mailbox_received_at = COALESCE(mailbox_received_at, received_at) WHERE mailbox_received_at IS NULL")
        conn.execute("UPDATE messages SET ingested_at = COALESCE(ingested_at, received_at) WHERE ingested_at IS NULL")
        session_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        if "role" not in session_columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")


def row_to_alias(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "address": row["address"],
        "local_part": row["local_part"],
        "domain": row["domain"],
        "label": row["label"],
        "source": row["source"],
        "status": row["status"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "last_message_at": row["last_message_at"],
        "last_sender": row["last_sender"],
        "message_count": row["message_count"],
    }


def row_to_message(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    from_name = decode_mime_text(row["from_name"] or "")
    subject = decode_mime_text(row["subject"] or "")
    text_body = row["text_body"] or ""
    html_body = row["html_body"] or ""
    readable_text = text_body or (html_to_text(html_body) if html_body else "")
    extracted_links = extract_links(text_body, html_body)
    extracted_otps = extract_otps(text_body, html_body)
    language_hint = infer_language_hint(subject, readable_text)
    return {
        "id": row["id"],
        "imap_uid": row["imap_uid"],
        "message_id": row["message_id"],
        "alias_id": row["alias_id"],
        "recipient_address": row["recipient_address"],
        "from_name": from_name,
        "from_email": row["from_email"],
        "subject": subject,
        "snippet": row["snippet"],
        "text_body": text_body,
        "html_body": html_body,
        "attachments": json.loads(row["attachments_json"] or "[]"),
        "extracted_links": extracted_links,
        "extracted_otps": extracted_otps,
        "raw_headers": json.loads(row["raw_headers_json"] or "{}"),
        "received_at": row["received_at"],
        "mailbox_received_at": row["mailbox_received_at"] or row["received_at"],
        "ingested_at": row["ingested_at"] or row["received_at"],
        "unread": bool(row["unread"]),
        "important": bool(row["important"]),
        "suppressed": bool(row["suppressed"]),
        "language_hint": language_hint,
        "can_translate": should_offer_translation(
            subject,
            readable_text,
            target_language=DEFAULT_TARGET_LANGUAGE,
            html_body=html_body,
        ),
    }


def row_to_message_summary(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    from_name = decode_mime_text(row["from_name"] or "")
    subject = decode_mime_text(row["subject"] or "")
    return {
        "id": row["id"],
        "alias_id": row["alias_id"],
        "recipient_address": row["recipient_address"],
        "from_name": from_name,
        "from_email": row["from_email"],
        "subject": subject,
        "snippet": row["snippet"],
        "received_at": row["received_at"],
        "mailbox_received_at": row["mailbox_received_at"] or row["received_at"],
        "ingested_at": row["ingested_at"] or row["received_at"],
        "unread": bool(row["unread"]),
        "important": bool(row["important"]),
        "has_links": bool(row["has_links"]),
        "has_otps": bool(row["has_otps"]),
    }


def create_session(token: str, username: str, role: str, expires_at: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions(token, username, role, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
            (token, username, role, expires_at, utc_now_iso()),
        )


def get_session(token: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT token, username, role, expires_at FROM sessions WHERE token = ?",
            (token,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def delete_session(token: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def delete_expired_sessions(now_iso: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_iso,))


def get_state(key: str, default: str = "") -> str:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_state(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_state(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def _refresh_alias_stats(conn: sqlite3.Connection, alias_id: int) -> None:
    conn.execute(
        """
        UPDATE aliases
        SET
            last_message_at = (
                SELECT MAX(received_at) FROM messages WHERE alias_id = aliases.id AND suppressed = 0
            ),
            last_sender = (
                SELECT COALESCE(from_email, from_name, '')
                FROM messages
                WHERE alias_id = aliases.id AND suppressed = 0
                ORDER BY received_at DESC, id DESC
                LIMIT 1
            ),
            message_count = (
                SELECT COUNT(*) FROM messages WHERE alias_id = aliases.id AND suppressed = 0
            )
        WHERE id = ?
        """,
        (alias_id,),
    )


def ensure_alias(
    address: str,
    *,
    source: str,
    label: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_address(address)
    local_part, domain = split_address(normalized)
    now_iso = utc_now_iso()

    with _connect() as conn:
        row = conn.execute("SELECT * FROM aliases WHERE address = ?", (normalized,)).fetchone()
        if row:
            updates: list[str] = []
            values: list[Any] = []
            if label is not None:
                updates.append("label = ?")
                values.append(label)
            if expires_at is not None:
                updates.append("expires_at = ?")
                values.append(expires_at)
            if source != "inbound" and row["source"] == "inbound":
                updates.append("source = ?")
                values.append(source)
            if updates:
                values.extend([normalized])
                conn.execute(f"UPDATE aliases SET {', '.join(updates)} WHERE address = ?", values)
                row = conn.execute("SELECT * FROM aliases WHERE address = ?", (normalized,)).fetchone()
            return row_to_alias(row)

        conn.execute(
            """
            INSERT INTO aliases(address, local_part, domain, label, source, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (normalized, local_part, domain, label, source, now_iso, expires_at),
        )
        row = conn.execute("SELECT * FROM aliases WHERE address = ?", (normalized,)).fetchone()
        return row_to_alias(row)


def list_aliases(search: str = "", status: str = "visible") -> list[dict[str, Any]]:
    query = "SELECT * FROM aliases WHERE 1=1"
    values: list[Any] = []
    if status == "visible":
        query += " AND status != 'deleted'"
    elif status != "all":
        query += " AND status = ?"
        values.append(status)
    if search:
        pattern = f"%{search.lower()}%"
        query += " AND (LOWER(address) LIKE ? OR LOWER(COALESCE(label, '')) LIKE ?)"
        values.extend([pattern, pattern])
    query += " ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'expired' THEN 1 ELSE 2 END, COALESCE(last_message_at, created_at) DESC"
    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
    return [row_to_alias(row) for row in rows]


def get_alias(alias_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM aliases WHERE id = ?", (alias_id,)).fetchone()
    return row_to_alias(row)


def get_alias_by_address(address: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM aliases WHERE address = ?", (normalize_address(address),)).fetchone()
    return row_to_alias(row)


def update_alias(alias_id: int, *, label: str | None = None, expires_at: str | None = None, status: str | None = None) -> dict[str, Any] | None:
    updates: list[str] = []
    values: list[Any] = []
    if label is not None:
        updates.append("label = ?")
        values.append(label)
    if expires_at is not None:
        updates.append("expires_at = ?")
        values.append(expires_at)
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if not updates:
        return get_alias(alias_id)
    values.append(alias_id)
    with _connect() as conn:
        conn.execute(f"UPDATE aliases SET {', '.join(updates)} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM aliases WHERE id = ?", (alias_id,)).fetchone()
    return row_to_alias(row)


def expire_alias(alias_id: int) -> dict[str, Any] | None:
    return update_alias(alias_id, status="expired")


def delete_alias(alias_id: int) -> dict[str, Any] | None:
    return update_alias(alias_id, status="deleted")


def reactivate_alias(alias_id: int, additional_hours: int | None = None) -> dict[str, Any] | None:
    expires_at = iso_in_hours(additional_hours) if additional_hours else None
    return update_alias(alias_id, status="active", expires_at=expires_at)


def cleanup_expired_aliases(now_iso: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE aliases SET status = 'expired' WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?",
            (now_iso,),
        )
    return cursor.rowcount


def cleanup_old_messages(cutoff_iso: str) -> int:
    with _connect() as conn:
        alias_rows = conn.execute(
            """
            SELECT DISTINCT alias_id
            FROM messages
            WHERE suppressed = 0 AND received_at < ? AND alias_id IS NOT NULL
            """,
            (cutoff_iso,),
        ).fetchall()
        cursor = conn.execute(
            "UPDATE messages SET suppressed = 1 WHERE suppressed = 0 AND received_at < ?",
            (cutoff_iso,),
        )
        for row in alias_rows:
            _refresh_alias_stats(conn, row["alias_id"])
    return cursor.rowcount


def store_message(payload: dict[str, Any]) -> dict[str, Any] | None:
    recipient_address = normalize_address(payload["recipient_address"])
    alias = get_alias_by_address(recipient_address)
    if alias is None:
        alias = ensure_alias(recipient_address, source="inbound", expires_at=iso_in_hours(settings.default_alias_hours))

    if alias["status"] != "active":
        return None

    with _connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO messages(
                imap_uid, message_id, alias_id, recipient_address, from_name, from_email, subject,
                snippet, text_body, html_body, attachments_json, extracted_links_json, extracted_otps_json, raw_headers_json,
                received_at, mailbox_received_at, ingested_at, unread, suppressed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """,
            (
                payload["imap_uid"],
                payload.get("message_id", ""),
                alias["id"],
                recipient_address,
                payload.get("from_name", ""),
                payload.get("from_email", ""),
                payload.get("subject", ""),
                payload.get("snippet", ""),
                payload.get("text_body", ""),
                payload.get("html_body", ""),
                json.dumps(payload.get("attachments", []), ensure_ascii=False),
                json.dumps(payload.get("extracted_links", []), ensure_ascii=False),
                json.dumps(payload.get("extracted_otps", []), ensure_ascii=False),
                json.dumps(payload.get("raw_headers", {}), ensure_ascii=False),
                payload["received_at"],
                payload.get("mailbox_received_at") or payload["received_at"],
                payload.get("ingested_at") or utc_now_iso(),
            ),
        )
        _refresh_alias_stats(conn, alias["id"])
        row = conn.execute("SELECT * FROM messages WHERE imap_uid = ?", (payload["imap_uid"],)).fetchone()
    return row_to_message(row)


def _build_message_scope(
    *,
    alias_id: int | None = None,
    filter_name: str = "all",
    search: str = "",
) -> tuple[str, list[Any]]:
    query = """
        FROM messages
        LEFT JOIN aliases ON aliases.id = messages.alias_id
        WHERE messages.suppressed = 0
          AND COALESCE(aliases.status, 'active') != 'deleted'
    """
    values: list[Any] = []
    if alias_id is not None:
        query += " AND alias_id = ?"
        values.append(alias_id)
    if filter_name == "unread":
        query += " AND unread = 1"
    elif filter_name == "important":
        query += " AND important = 1"
    elif filter_name == "otp":
        query += " AND extracted_otps_json != '[]'"
    elif filter_name == "links":
        query += " AND extracted_links_json != '[]'"
    if search:
        pattern = f"%{search.lower()}%"
        query += """
            AND (
                LOWER(COALESCE(messages.recipient_address, '')) LIKE ?
                OR LOWER(COALESCE(aliases.address, '')) LIKE ?
                OR LOWER(COALESCE(aliases.local_part, '')) LIKE ?
                OR LOWER(COALESCE(subject, '')) LIKE ?
                OR LOWER(COALESCE(from_name, '')) LIKE ?
                OR LOWER(COALESCE(from_email, '')) LIKE ?
                OR LOWER(COALESCE(snippet, '')) LIKE ?
            )
        """
        values.extend([pattern, pattern, pattern, pattern, pattern, pattern, pattern])
    return query, values


def list_messages(*, alias_id: int | None = None, filter_name: str = "all", search: str = "", limit: int = 200) -> list[dict[str, Any]]:
    scope_query, values = _build_message_scope(alias_id=alias_id, filter_name=filter_name, search=search)
    query = f"SELECT messages.* {scope_query}"
    query += " ORDER BY received_at DESC LIMIT ?"
    values.append(limit)
    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
    return [row_to_message(row) for row in rows]


def delete_messages_by_scope(*, alias_id: int | None = None, filter_name: str = "all", search: str = "") -> dict[str, Any]:
    scope_query, values = _build_message_scope(alias_id=alias_id, filter_name=filter_name, search=search)
    query = f"SELECT messages.id, messages.alias_id, messages.recipient_address {scope_query}"

    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
        if not rows:
            return {"deleted_count": 0, "recipient_addresses": []}

        message_ids = [row["id"] for row in rows]
        alias_ids = sorted({row["alias_id"] for row in rows if row["alias_id"] is not None})
        recipient_addresses = sorted({row["recipient_address"] for row in rows if row["recipient_address"]})
        placeholders = ", ".join("?" for _ in message_ids)
        conn.execute(f"UPDATE messages SET suppressed = 1 WHERE id IN ({placeholders})", message_ids)
        for alias_id_value in alias_ids:
            _refresh_alias_stats(conn, alias_id_value)
    return {"deleted_count": len(message_ids), "recipient_addresses": recipient_addresses}


def list_public_messages(*, recipient_address: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                messages.id,
                messages.alias_id,
                messages.recipient_address,
                messages.from_name,
                messages.from_email,
                messages.subject,
                messages.snippet,
                messages.received_at,
                messages.mailbox_received_at,
                messages.ingested_at,
                messages.unread,
                messages.important,
                CASE WHEN messages.extracted_links_json != '[]' THEN 1 ELSE 0 END AS has_links,
                CASE WHEN messages.extracted_otps_json != '[]' THEN 1 ELSE 0 END AS has_otps
            FROM messages
            LEFT JOIN aliases ON aliases.id = messages.alias_id
            WHERE messages.suppressed = 0
              AND messages.recipient_address = ?
              AND COALESCE(aliases.status, 'active') != 'deleted'
            ORDER BY messages.received_at DESC
            """,
            (normalize_address(recipient_address),),
        ).fetchall()
    return [row_to_message_summary(row) for row in rows]


def list_recent_message_timings(*, limit: int = 20) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                imap_uid,
                message_id,
                recipient_address,
                from_email,
                subject,
                received_at,
                mailbox_received_at,
                ingested_at
            FROM messages
            WHERE suppressed = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "imap_uid": row["imap_uid"],
                "message_id": row["message_id"],
                "recipient_address": row["recipient_address"],
                "from_email": row["from_email"],
                "subject": decode_mime_text(row["subject"] or ""),
                "received_at": row["received_at"],
                "mailbox_received_at": row["mailbox_received_at"] or row["received_at"],
                "ingested_at": row["ingested_at"] or row["received_at"],
            }
        )
    return items


def get_message(message_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(row)


def get_message_for_address(message_id: int, recipient_address: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT messages.*
            FROM messages
            LEFT JOIN aliases ON aliases.id = messages.alias_id
            WHERE messages.id = ?
              AND messages.suppressed = 0
              AND messages.recipient_address = ?
              AND COALESCE(aliases.status, 'active') != 'deleted'
            """,
            (message_id, normalize_address(recipient_address)),
        ).fetchone()
    return row_to_message(row)


def mark_message_read(message_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        conn.execute("UPDATE messages SET unread = 0 WHERE id = ?", (message_id,))
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(row)


def set_message_important(message_id: int, important: bool) -> dict[str, Any] | None:
    with _connect() as conn:
        conn.execute("UPDATE messages SET important = ? WHERE id = ?", (1 if important else 0, message_id))
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(row)


def delete_message(message_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        existing = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if existing is None:
            return None
        conn.execute("UPDATE messages SET suppressed = 1 WHERE id = ?", (message_id,))
        if existing["alias_id"] is not None:
            _refresh_alias_stats(conn, existing["alias_id"])
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(row)
