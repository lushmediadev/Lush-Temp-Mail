from __future__ import annotations

from typing import Any

import httpx

from .parser import html_to_text


GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
TRANSLATE_CHUNK_SIZE = 1800
DEFAULT_TARGET_LANGUAGE = "vi"


def translate_email_content(subject: str, body: str, target_language: str = DEFAULT_TARGET_LANGUAGE) -> dict[str, Any]:
    normalized_target = (target_language or DEFAULT_TARGET_LANGUAGE).strip().lower() or DEFAULT_TARGET_LANGUAGE
    translated_subject, subject_source = translate_text(subject, target_language=normalized_target)
    translated_body, body_source = translate_text(body, target_language=normalized_target)
    source_language = subject_source or body_source or "und"

    return {
        "source_language": source_language,
        "target_language": normalized_target,
        "translated_subject": translated_subject,
        "translated_body": translated_body,
    }


def translate_message(message: dict[str, Any], target_language: str = DEFAULT_TARGET_LANGUAGE) -> dict[str, Any]:
    subject = message.get("subject") or ""
    body_text = (message.get("text_body") or "").strip()
    if not body_text:
        body_html = (message.get("html_body") or "").strip()
        if body_html:
            body_text = html_to_text(body_html)
    return translate_email_content(subject, body_text, target_language=target_language)


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
