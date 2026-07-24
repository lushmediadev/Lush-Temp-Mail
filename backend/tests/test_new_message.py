from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app import main


ROOT = Path(__file__).resolve().parents[2]


def test_standalone_send_endpoint_sends_and_stores_message(monkeypatch):
    captured = {}

    def fake_send_composed_message(**kwargs):
        captured.update(kwargs)
        return {
            "mode": kwargs["mode"],
            "to": ["receiver@example.com"],
            "cc": [],
            "subject": kwargs["subject"],
            "from": kwargs["from_value"],
            "message_id": "<new-message@lushmedia.net>",
            "attachment_count": 0,
        }

    def fake_store_sent_message(payload):
        captured["stored"] = payload
        return {"id": 42, **payload}

    monkeypatch.setattr(main, "send_composed_message", fake_send_composed_message)
    monkeypatch.setattr(main.db, "store_sent_message", fake_store_sent_message)

    result = main.send_new_message(
        {
            "from_alias": "sales@lushmedia.net",
            "to": "receiver@example.com",
            "cc": "",
            "subject": "Email mới",
            "body": "Nội dung gửi mới",
        },
        _session={"user_id": 1, "role": "admin"},
    )

    assert result["ok"] is True
    assert captured["source_message"] == {}
    assert captured["mode"] == "send"
    assert captured["from_value"] == "sales@lushmedia.net"
    assert captured["attachments"] == []
    assert captured["stored"]["source_message_id"] is None
    assert captured["stored"]["mode"] == "send"


def test_standalone_send_endpoint_hides_delivery_internals(monkeypatch):
    def fail_delivery(**_kwargs):
        raise RuntimeError("<!DOCTYPE html><html>gateway failure</html>")

    monkeypatch.setattr(main, "send_composed_message", fail_delivery)

    with pytest.raises(HTTPException) as raised:
        main.send_new_message(
            {
                "from_alias": "sales@lushmedia.net",
                "to": "receiver@example.com",
                "cc": "",
                "subject": "Email mới",
                "body": "Nội dung gửi mới",
            },
            _session={"user_id": 1, "role": "admin"},
        )

    assert raised.value.status_code == 502
    assert raised.value.detail == "Gửi mail thất bại. Máy chủ gửi mail chưa chấp nhận yêu cầu."
    assert "<html>" not in raised.value.detail


def test_admin_ui_exposes_new_message_composer():
    index_html = (ROOT / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "app.js").read_text(encoding="utf-8")

    assert 'id="newMessageBtn"' in index_html
    assert 'id="newMessageModal"' in index_html
    assert 'id="newMessageFrom"' in index_html
    assert "app.js?v=20260724-lushmail-compose-sender-fix" in index_html
    assert "function openNewMessageComposer()" in app_js
    assert "function sendNewMessage(event)" in app_js
    assert "'/api/messages/send'" in app_js
    assert "from_alias: dom.newMessageFrom.value" in app_js
    assert "Máy chủ tạm thời không phản hồi. Vui lòng thử lại." in app_js
    assert "return 'Mới';" in app_js
