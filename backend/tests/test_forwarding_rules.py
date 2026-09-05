import pytest
from fastapi import HTTPException

from backend.app import db, imap_sync, main
from backend.app.config import settings


def _message_payload(uid: int, recipient: str = "lush@lushmedia.net") -> dict:
    return {
        "imap_mailbox": "contact@lushmedia.net",
        "imap_uid": uid,
        "message_id": f"<message-{uid}@example.com>",
        "recipient_address": recipient,
        "from_name": "OpenAI",
        "from_email": "support@example.com",
        "subject": "Appeal update",
        "snippet": "Your appeal has been reviewed.",
        "text_body": "Your appeal has been reviewed.",
        "html_body": "",
        "attachments": [
            {
                "index": 0,
                "filename": "result.pdf",
                "content_type": "application/pdf",
                "disposition": "attachment",
                "size_bytes": 4,
            }
        ],
        "attachment_payloads": [
            {
                "index": 0,
                "filename": "result.pdf",
                "content_type": "application/pdf",
                "disposition": "attachment",
                "size_bytes": 4,
                "content": b"test",
            }
        ],
        "extracted_links": [],
        "extracted_otps": [],
        "raw_headers": {},
        "received_at": "2026-09-04T12:00:00+00:00",
    }


def _init_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "forwarding.db")
    db.init_db()


def test_rule_only_enqueues_new_messages_and_never_duplicates(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    db.store_message(_message_payload(1))
    db.create_forwarding_rule("lush@lushmedia.net", "owner@gmail.com")

    assert db.list_due_forwarding_deliveries() == []

    db.store_message(_message_payload(2))
    due = db.list_due_forwarding_deliveries()
    assert len(due) == 1
    assert due[0]["source_address"] == "lush@lushmedia.net"
    assert due[0]["target_address"] == "owner@gmail.com"

    db.store_message(_message_payload(2))
    assert len(db.list_due_forwarding_deliveries()) == 1


def test_forwarding_worker_sends_body_and_cached_attachments_once(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    db.create_forwarding_rule("lush@lushmedia.net", "owner@gmail.com")
    db.store_message(_message_payload(3))
    captured = {}
    stored_sent = []

    def fake_send_automatic_forward(**kwargs):
        captured.update(kwargs)
        return {"message_id": "<forwarded@lushmedia.net>"}

    monkeypatch.setattr(imap_sync, "send_automatic_forward", fake_send_automatic_forward)
    monkeypatch.setattr(db, "store_sent_message", lambda payload: stored_sent.append(payload) or {"id": 99})
    service = imap_sync.MailSyncService()
    service._process_pending_forwards()

    assert captured["target_address"] == "owner@gmail.com"
    assert captured["source_message"]["recipient_address"] == "lush@lushmedia.net"
    assert captured["attachments"][0]["content"] == b"test"
    assert stored_sent[0]["mode"] == "auto-forward"
    assert stored_sent[0]["to"] == ["owner@gmail.com"]
    assert stored_sent[0]["attachments"][0]["content"] == b"test"
    assert db.list_due_forwarding_deliveries() == []
    rule = db.list_forwarding_rules()[0]
    assert rule["last_status"] == "forwarded"
    assert rule["last_forwarded_at"] is not None


def test_forwarding_worker_keeps_failed_delivery_for_retry(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    db.create_forwarding_rule("lush@lushmedia.net", "owner@gmail.com")
    db.store_message(_message_payload(4))

    def fail_forward(**_kwargs):
        raise RuntimeError("SMTP unavailable")

    monkeypatch.setattr(imap_sync, "send_automatic_forward", fail_forward)
    imap_sync.MailSyncService()._process_pending_forwards()

    rule = db.list_forwarding_rules()[0]
    assert rule["last_status"] == "retrying"
    assert rule["last_error"] == "SMTP unavailable"


def test_forwarding_rule_supports_multiple_sources_and_targets(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    rule = db.create_forwarding_rule(
        ["first@lushmedia.net", "second@lushmedia.net"],
        ["owner@gmail.com", "backup@outlook.com"],
    )

    assert rule["source_addresses"] == ["first@lushmedia.net", "second@lushmedia.net"]
    assert rule["target_addresses"] == ["backup@outlook.com", "owner@gmail.com"]
    assert len(db.list_forwarding_rules(search="backup@outlook")) == 1

    db.store_message(_message_payload(5, recipient="second@lushmedia.net"))
    due = db.list_due_forwarding_deliveries()
    assert len(due) == 2
    assert {item["target_address"] for item in due} == {"backup@outlook.com", "owner@gmail.com"}

    updated = db.update_forwarding_rule(
        rule["id"],
        source_addresses="third@lushmedia.net, second@lushmedia.net",
        target_addresses="owner@gmail.com",
    )
    assert updated["source_addresses"] == ["second@lushmedia.net", "third@lushmedia.net"]
    assert updated["target_addresses"] == ["owner@gmail.com"]


def test_forwarding_targets_retry_independently(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    db.create_forwarding_rule("first@lushmedia.net", "owner@gmail.com, backup@outlook.com")
    db.store_message(_message_payload(7, recipient="first@lushmedia.net"))
    attempts = []
    stored_sent = []

    def fake_send(**kwargs):
        attempts.append(kwargs["target_address"])
        if kwargs["target_address"] == "owner@gmail.com":
            raise RuntimeError("Gmail temporarily unavailable")
        return {"message_id": "<forwarded-target@lushmedia.net>"}

    monkeypatch.setattr(imap_sync, "send_automatic_forward", fake_send)
    monkeypatch.setattr(db, "store_sent_message", lambda payload: stored_sent.append(payload) or {"id": 100})
    imap_sync.MailSyncService()._process_pending_forwards()

    assert set(attempts) == {"backup@outlook.com", "owner@gmail.com"}
    assert [item["to"] for item in stored_sent] == [["backup@outlook.com"]]
    with db._connect() as conn:
        statuses = conn.execute(
            "SELECT target_address, status FROM forwarding_delivery_targets ORDER BY target_address"
        ).fetchall()
    assert [(row["target_address"], row["status"]) for row in statuses] == [
        ("backup@outlook.com", "forwarded"),
        ("owner@gmail.com", "retrying"),
    ]


def test_one_message_is_available_for_all_recipient_aliases(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    payload = _message_payload(6, recipient="first@lushmedia.net")
    payload["recipient_addresses"] = ["first@lushmedia.net", "second@lushmedia.net"]

    stored = db.store_message(payload)

    assert stored["recipient_address"] == "first@lushmedia.net"
    second_inbox = db.list_public_messages(recipient_address="second@lushmedia.net")
    assert len(second_inbox) == 1
    assert second_inbox[0]["message_id"] == "<message-6@example.com>"
    assert second_inbox[0]["recipient_address"] == "second@lushmedia.net"
    assert db.get_message_for_address(stored["id"], "second@lushmedia.net")["id"] == stored["id"]
    all_inbox = db.list_messages()
    assert {(item["message_id"], item["recipient_address"]) for item in all_inbox} == {
        ("<message-6@example.com>", "first@lushmedia.net"),
        ("<message-6@example.com>", "second@lushmedia.net"),
    }


def test_forwarding_api_rejects_internal_destination():
    with pytest.raises(HTTPException) as raised:
        main.create_forwarding_rule(
            {
                "source_address": "lush@lushmedia.net",
                "target_address": "loop@lushmedia.net",
            },
            _session={"role": "admin"},
        )

    assert raised.value.status_code == 400
    assert "tránh vòng lặp" in raised.value.detail
