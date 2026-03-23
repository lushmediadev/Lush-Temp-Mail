from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any

import httpx

from .parser import html_to_text


GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
TRANSLATE_CHUNK_SIZE = 1800
DEFAULT_TARGET_LANGUAGE = "vi"
TRANSLATION_TOKEN_TEMPLATE = "\uE000LUSHSEG{index:04d}\uE001"
VIETNAMESE_DIACRITIC_RE = re.compile(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.IGNORECASE)
VIETNAMESE_WORD_RE = re.compile(
    r"\b(?:xin|chào|mã|xác|nhận|đăng|nhập|hoàn|tất|thiết|lập|bạn|vui|lòng|tiếp|tục|miễn|phí|trân|trọng|mật|khẩu)\b",
    re.IGNORECASE,
)
HTML_TRANSLATION_SKIP_TAGS = {"script", "style", "head", "svg", "code", "pre", "noscript"}


def infer_language_hint(*parts: str) -> str:
    combined = " ".join(str(part or "").strip() for part in parts if str(part or "").strip())
    if not combined:
        return "und"

    if VIETNAMESE_DIACRITIC_RE.search(combined):
        return "vi"

    word_hits = len(VIETNAMESE_WORD_RE.findall(combined))
    if word_hits >= 2:
        return "vi"

    return "und"


def should_offer_translation(
    subject: str,
    body_text: str,
    *,
    target_language: str = DEFAULT_TARGET_LANGUAGE,
    html_body: str = "",
) -> bool:
    normalized_target = (target_language or DEFAULT_TARGET_LANGUAGE).strip().lower() or DEFAULT_TARGET_LANGUAGE
    readable_text = body_text or (html_to_text(html_body) if html_body else "")
    if not (subject or readable_text or html_body):
        return False
    hint = infer_language_hint(subject, readable_text)
    return hint != normalized_target


def translate_email_content(
    subject: str,
    body: str,
    *,
    html_body: str = "",
    target_language: str = DEFAULT_TARGET_LANGUAGE,
) -> dict[str, Any]:
    normalized_target = (target_language or DEFAULT_TARGET_LANGUAGE).strip().lower() or DEFAULT_TARGET_LANGUAGE
    readable_body = body or (html_to_text(html_body) if html_body else "")
    source_hint = infer_language_hint(subject, readable_body)

    if source_hint == normalized_target:
        return build_skipped_translation_payload(
            subject=subject,
            body=readable_body,
            html_body=html_body,
            source_language=source_hint,
            target_language=normalized_target,
        )

    translated_subject, subject_source = translate_text(subject, target_language=normalized_target)

    if html_body:
        translated_html, html_source = translate_html_document(html_body, target_language=normalized_target)
        translated_body = html_to_text(translated_html) if translated_html else readable_body
        content_source = first_known_language(html_source, source_hint)
        source_language = first_known_language(html_source, subject_source, source_hint)
        if content_source == normalized_target:
            return build_skipped_translation_payload(
                subject=subject,
                body=readable_body,
                html_body=html_body,
                source_language=source_language,
                target_language=normalized_target,
            )
        return {
            "source_language": source_language,
            "target_language": normalized_target,
            "translated_subject": translated_subject or subject,
            "translated_body": translated_body or readable_body,
            "translated_html": translated_html or html_body,
            "skipped": False,
            "skip_reason": "",
        }

    translated_body, body_source = translate_text(readable_body, target_language=normalized_target)
    content_source = first_known_language(body_source, source_hint)
    source_language = first_known_language(body_source, subject_source, source_hint)
    if content_source == normalized_target:
        return build_skipped_translation_payload(
            subject=subject,
            body=readable_body,
            html_body="",
            source_language=source_language,
            target_language=normalized_target,
        )
    return {
        "source_language": source_language,
        "target_language": normalized_target,
        "translated_subject": translated_subject or subject,
        "translated_body": translated_body or readable_body,
        "translated_html": "",
        "skipped": False,
        "skip_reason": "",
    }


def translate_message(message: dict[str, Any], target_language: str = DEFAULT_TARGET_LANGUAGE) -> dict[str, Any]:
    subject = message.get("subject") or ""
    body_text = (message.get("text_body") or "").strip()
    body_html = (message.get("html_body") or "").strip()
    if not body_text and body_html:
        body_text = html_to_text(body_html)

    return translate_email_content(
        subject,
        body_text,
        html_body=body_html,
        target_language=target_language,
    )


def translate_html_document(html_body: str, target_language: str = DEFAULT_TARGET_LANGUAGE) -> tuple[str, str]:
    parser = HtmlTranslationParser()
    parser.feed(str(html_body or ""))
    parser.close()

    if not parser.segments:
        return str(html_body or ""), "und"

    translated_segments, detected_source = translate_texts(
        [segment["core"] for segment in parser.segments],
        target_language=target_language,
    )
    return parser.render(translated_segments), detected_source


def translate_texts(texts: list[str], target_language: str = DEFAULT_TARGET_LANGUAGE) -> tuple[list[str], str]:
    if not texts:
        return [], "und"

    results = list(texts)
    detected_source = "und"
    pending_indexes: list[int] = []
    pending_texts: list[str] = []
    pending_length = 0

    def flush_batch() -> None:
        nonlocal pending_indexes, pending_texts, pending_length, detected_source
        if not pending_texts:
            return
        translated_batch, batch_source = translate_text_batch(pending_texts, target_language=target_language)
        if detected_source == "und" and batch_source != "und":
            detected_source = batch_source
        for index, translated in zip(pending_indexes, translated_batch):
            results[index] = translated
        pending_indexes = []
        pending_texts = []
        pending_length = 0

    for index, text in enumerate(texts):
        if not str(text or "").strip():
            continue

        candidate_length = len(text) + 24
        if pending_texts and pending_length + candidate_length > TRANSLATE_CHUNK_SIZE:
            flush_batch()

        pending_indexes.append(index)
        pending_texts.append(text)
        pending_length += candidate_length

    flush_batch()
    return results, detected_source


def translate_text_batch(texts: list[str], target_language: str = DEFAULT_TARGET_LANGUAGE) -> tuple[list[str], str]:
    if not texts:
        return [], "und"
    if len(texts) == 1:
        translated, detected_source = translate_text(texts[0], target_language=target_language)
        return [translated], detected_source

    tokens = [TRANSLATION_TOKEN_TEMPLATE.format(index=index) for index in range(len(texts) - 1)]
    combined_parts: list[str] = []
    for index, text in enumerate(texts):
        if index:
            combined_parts.append(tokens[index - 1])
        combined_parts.append(text)
    combined_text = "".join(combined_parts)
    translated_combined, detected_source = translate_text(combined_text, target_language=target_language)
    split_texts = split_translated_batch(translated_combined, tokens)
    if split_texts is None:
        fallback_results = []
        fallback_source = "und"
        for text in texts:
            translated_text, text_source = translate_text(text, target_language=target_language)
            fallback_results.append(translated_text)
            if fallback_source == "und" and text_source != "und":
                fallback_source = text_source
        return fallback_results, fallback_source
    return split_texts, detected_source


def split_translated_batch(translated: str, tokens: list[str]) -> list[str] | None:
    if not tokens:
        return [translated]

    parts: list[str] = []
    cursor = 0
    for token in tokens:
        token_index = translated.find(token, cursor)
        if token_index < 0:
            return None
        parts.append(translated[cursor:token_index])
        cursor = token_index + len(token)
    parts.append(translated[cursor:])
    return parts


def translate_text(text: str, target_language: str = DEFAULT_TARGET_LANGUAGE) -> tuple[str, str]:
    cleaned = str(text or "")
    if not cleaned.strip():
        return "", "und"

    translated_parts: list[str] = []
    detected_source = "und"

    with httpx.Client(timeout=20.0, headers={"User-Agent": "LushMail/1.0"}) as client:
        for chunk in chunk_text(cleaned):
            response = client.get(
                GOOGLE_TRANSLATE_URL,
                params={
                    "client": "gtx",
                    "sl": "auto",
                    "tl": target_language,
                    "dt": "t",
                    "q": chunk,
                },
            )
            response.raise_for_status()
            payload = response.json()
            translated_parts.append(parse_translated_text(payload))
            if detected_source == "und":
                detected_source = parse_detected_language(payload)

    return "".join(translated_parts), detected_source


def build_skipped_translation_payload(
    *,
    subject: str,
    body: str,
    html_body: str,
    source_language: str,
    target_language: str,
) -> dict[str, Any]:
    return {
        "source_language": source_language or target_language or "und",
        "target_language": target_language,
        "translated_subject": subject,
        "translated_body": body,
        "translated_html": html_body,
        "skipped": True,
        "skip_reason": "same_language",
    }


def first_known_language(*languages: str) -> str:
    for language in languages:
        normalized = (language or "").strip().lower()
        if normalized and normalized != "und":
            return normalized
    return "und"


def chunk_text(text: str, size: int = TRANSLATE_CHUNK_SIZE) -> list[str]:
    chunks: list[str] = []
    buffer = ""

    for line in text.splitlines(keepends=True):
        if len(line) > size:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(split_large_piece(line, size))
            continue

        if buffer and len(buffer) + len(line) > size:
            chunks.append(buffer)
            buffer = line
        else:
            buffer += line

    if buffer:
        chunks.append(buffer)

    return chunks or [text]


def split_large_piece(text: str, size: int) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)]


def parse_translated_text(payload: Any) -> str:
    segments = payload[0] if isinstance(payload, list) and payload else []
    translated = []
    for segment in segments:
        if isinstance(segment, list) and segment:
            translated.append(str(segment[0] or ""))
    return "".join(translated)


def parse_detected_language(payload: Any) -> str:
    if isinstance(payload, list) and len(payload) > 2 and isinstance(payload[2], str) and payload[2].strip():
        return payload[2].strip().lower()
    return "und"


def has_translatable_text(value: str) -> bool:
    stripped = str(value or "").strip()
    return bool(stripped and re.search(r"[A-Za-zÀ-ỹ0-9]", stripped))


def split_text_whitespace(value: str) -> tuple[str, str, str]:
    match = re.match(r"^(\s*)(.*?)(\s*)$", value, re.DOTALL)
    if not match:
        return "", value, ""
    return match.group(1), match.group(2), match.group(3)


class HtmlTranslationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.output_parts: list[str] = []
        self.segments: list[dict[str, str]] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.output_parts.append(self.get_starttag_text() or f"<{tag}>")
        if tag.lower() in HTML_TRANSLATION_SKIP_TAGS:
            self.skip_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.output_parts.append(self.get_starttag_text() or f"<{tag} />")

    def handle_endtag(self, tag: str) -> None:
        self.output_parts.append(f"</{tag}>")
        if tag.lower() in HTML_TRANSLATION_SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not has_translatable_text(data):
            self.output_parts.append(data)
            return

        prefix, core, suffix = split_text_whitespace(data)
        if not core:
            self.output_parts.append(data)
            return

        token = TRANSLATION_TOKEN_TEMPLATE.format(index=len(self.segments))
        self.output_parts.append(token)
        self.segments.append(
            {
                "prefix": prefix,
                "core": core,
                "suffix": suffix,
            }
        )

    def handle_entityref(self, name: str) -> None:
        self.output_parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.output_parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self.output_parts.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self.output_parts.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self.output_parts.append(f"<?{data}>")

    def unknown_decl(self, data: str) -> None:
        self.output_parts.append(f"<![{data}]>")

    def render(self, translated_segments: list[str]) -> str:
        rendered = "".join(self.output_parts)
        for index, translated in enumerate(translated_segments):
            token = TRANSLATION_TOKEN_TEMPLATE.format(index=index)
            segment = self.segments[index]
            replacement = f"{segment['prefix']}{html.escape(translated, quote=False)}{segment['suffix']}"
            rendered = rendered.replace(token, replacement, 1)
        return rendered
