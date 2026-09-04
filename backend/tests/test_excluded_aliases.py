from backend.app import db
from backend.app.config import settings


def setup_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "excluded_aliases.db")
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "admin-pass")
    monkeypatch.setattr(settings, "user_username", "user")
    monkeypatch.setattr(settings, "user_password", "user-pass")
    db.init_db()


def message_payload(address: str, uid: int = 1) -> dict:
    return {
        "imap_mailbox": "inbox@example.com",
        "imap_uid": uid,
        "message_id": f"<message-{uid}@example.com>",
        "recipient_address": address,
        "from_name": "Sender",
        "from_email": "sender@example.com",
        "subject": "Spam",
        "snippet": "spam message",
        "text_body": "spam message",
        "html_body": "",
        "attachments": [],
        "attachment_payloads": [],
        "extracted_links": [],
        "extracted_otps": [],
        "raw_headers": {},
        "received_at": "2026-05-13T10:00:00+00:00",
    }


def test_excluded_alias_blocks_new_messages(monkeypatch, tmp_path):
    setup_temp_db(monkeypatch, tmp_path)

    item = db.create_excluded_alias("Spam@lushmedia.net", reason="spam")
    stored = db.store_message(message_payload("spam@lushmedia.net"))

    assert item["address"] == "spam@lushmedia.net"
    assert stored is None
    assert db.list_messages(search="spam") == []
    assert db.list_aliases(search="spam") == []


def test_creating_excluded_alias_hides_existing_messages(monkeypatch, tmp_path):
    setup_temp_db(monkeypatch, tmp_path)
    stored = db.store_message(message_payload("oldspam@lushmedia.net"))

    assert stored is not None
    assert len(db.list_messages(search="oldspam")) == 1

    db.create_excluded_alias("oldspam@lushmedia.net")

    assert db.list_messages(search="oldspam") == []
    alias = db.get_alias_by_address("oldspam@lushmedia.net")
    assert alias["message_count"] == 0


def test_message_list_returns_summary_without_full_body(monkeypatch, tmp_path):
    setup_temp_db(monkeypatch, tmp_path)
    payload = message_payload("summary@lushmedia.net")
    payload["text_body"] = "full text that belongs only in the detail view"
    payload["html_body"] = "<html><body>large rendered body</body></html>"
    payload["extracted_links"] = [{"url": "https://example.com", "text": "example"}]
    payload["extracted_otps"] = [{"code": "123456"}]
    db.store_message(payload)

    item = db.list_messages(search="summary")[0]

    assert item["snippet"] == "spam message"
    assert item["has_links"] is True
    assert item["has_otps"] is True
    assert "text_body" not in item
    assert "html_body" not in item
    assert "raw_headers" not in item
