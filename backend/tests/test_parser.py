from email import message_from_string

from backend.app.parser import extract_links, extract_otps, extract_recipient


def test_extract_recipient_prefers_original_alias_over_central_mailbox():
    message = message_from_string(
        "From: service@example.com\n"
        "To: contact@congmail.top\n"
        "Delivered-To: abc123@congmail.top\n"
        "Subject: Test\n\n"
        "Body"
    )
    assert extract_recipient(message, "congmail.top", "contact@congmail.top") == "abc123@congmail.top"


def test_extract_links_and_otps():
    text = "Ma xac nhan cua ban la 847291. Xac minh tai https://service.example/verify?token=abc"
    links = extract_links(text, "")
    otps = extract_otps(text, "")
    assert links[0]["type"] == "verify"
    assert any(item["code"] == "847291" for item in otps)
