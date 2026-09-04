import pytest

from backend.app import mailer


def test_forward_sends_cc_and_attachments(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, *_args, **_kwargs):
            pass

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, *_args):
            pass

        def send_message(self, message, from_addr=None, to_addrs=None):
            sent["message"] = message
            sent["from_addr"] = from_addr
            sent["to_addrs"] = to_addrs

        def quit(self):
            pass

    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mailer.settings, "smtp_security", "none")
    monkeypatch.setattr(mailer.settings, "smtp_password", "")
    monkeypatch.setattr(mailer.settings, "smtp_from_address", "contact@lushmedia.net")

    result = mailer.send_composed_message(
        source_message={"message_id": "<source@example.com>"},
        mode="forward",
        from_value="billing",
        to_value="receiver@example.com",
        cc_value="copy@example.com",
        subject="Fwd: invoice",
        body="Please see attachments.",
        attachments=[
            {
                "filename": "invoice.pdf",
                "content_type": "application/pdf",
                "content": b"%PDF-1.4",
                "size_bytes": 8,
            }
        ],
    )

    message = sent["message"]
    assert sent["from_addr"] == "contact@lushmedia.net"
    assert "billing@lushmedia.net" in message["From"]
    assert message["Reply-To"] == "billing@lushmedia.net"
    assert sent["to_addrs"] == ["receiver@example.com", "copy@example.com"]
    assert message["Cc"] == "copy@example.com"
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "invoice.pdf"
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_payload(decode=True) == b"%PDF-1.4"
    assert result["from"] == "billing@lushmedia.net"
    assert result["attachment_count"] == 1


def test_sender_alias_must_use_configured_mail_domain(monkeypatch):
    monkeypatch.setattr(mailer.settings, "mail_domain", "lushmedia.net")

    with pytest.raises(ValueError, match="Chỉ hỗ trợ alias @lushmedia.net"):
        mailer.send_composed_message(
            source_message={},
            mode="send",
            from_value="spoof@example.com",
            to_value="receiver@example.com",
            cc_value="",
            subject="Test",
            body="Test body",
        )


def test_attachment_total_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(mailer, "MAX_ATTACHMENT_TOTAL_BYTES", 4)

    with pytest.raises(ValueError, match="18 MB"):
        mailer.validate_outgoing_attachments(
            [
                {
                    "filename": "video.mp4",
                    "content_type": "video/mp4",
                    "content": b"12345",
                }
            ]
        )


def test_automatic_forward_preserves_source_context(monkeypatch):
    captured = {}

    def fake_send_composed_message(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(mailer, "send_composed_message", fake_send_composed_message)
    result = mailer.send_automatic_forward(
        source_message={
            "recipient_address": "lush@lushmedia.net",
            "from_name": "OpenAI Support",
            "from_email": "support@example.com",
            "subject": "Appeal result",
            "text_body": "Approved",
            "received_at": "2026-09-04T12:00:00+00:00",
            "html_body": "<p>Approved</p>",
        },
        target_address="owner@gmail.com",
        attachments=[{"filename": "result.pdf", "content": b"pdf"}],
    )

    assert result == {"ok": True}
    assert captured["from_value"] == "lush@lushmedia.net"
    assert captured["to_value"] == "owner@gmail.com"
    assert captured["subject"] == "Fwd: Appeal result"
    assert "OpenAI Support <support@example.com>" in captured["body"]
    assert captured["attachments"][0]["filename"] == "result.pdf"
    assert captured["html_body"] == "<p>Approved</p>"
