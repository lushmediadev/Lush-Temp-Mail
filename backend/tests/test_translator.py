from backend.app import translator


def test_translate_html_document_preserves_layout_markup(monkeypatch):
    def fake_translate_texts(texts, target_language="vi"):
        return ([f"VI:{text}" for text in texts], "en")

    monkeypatch.setattr(translator, "translate_texts", fake_translate_texts)

    html = (
        '<html><body>'
        '<h1>Pick up where you left off</h1>'
        '<p>It only takes a minute.</p>'
        '<a href="https://example.com/finish">Finish account setup</a>'
        '</body></html>'
    )

    translated_html, source_language = translator.translate_html_document(html, target_language="vi")

    assert source_language == "en"
    assert '<a href="https://example.com/finish">VI:Finish account setup</a>' in translated_html
    assert "<h1>VI:Pick up where you left off</h1>" in translated_html
    assert "<p>VI:It only takes a minute.</p>" in translated_html


def test_translate_email_content_skips_when_message_is_already_vietnamese():
    result = translator.translate_email_content(
        "Hoàn tất thiết lập tài khoản của bạn",
        "Mã xác nhận của bạn là 123456",
        target_language="vi",
    )

    assert result["skipped"] is True
    assert result["skip_reason"] == "same_language"
    assert result["source_language"] == "vi"
    assert result["translated_subject"] == "Hoàn tất thiết lập tài khoản của bạn"


def test_should_offer_translation_hides_button_for_vietnamese_mail():
    assert translator.should_offer_translation(
        "Hoàn tất thiết lập tài khoản của bạn",
        "Tiếp tục từ nơi bạn dừng lại",
        target_language="vi",
    ) is False
    assert translator.should_offer_translation(
        "Finish setting up your account",
        "Pick up where you left off",
        target_language="vi",
    ) is True
