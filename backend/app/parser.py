from __future__ import annotations

import html
import re
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any

from .utils import normalize_address, utc_now


RECIPIENT_HEADERS = [
    "X-Original-To",
    "Delivered-To",
    "Envelope-To",
    "X-Envelope-To",
    "Original-Recipient",
    "To",
    "Cc",
]

URL_RE = re.compile(r"https?://[^\s<>\"]+")
OTP_CONTEXT_RE = re.compile(
    r"(?i)(?:otp|verification code|verify code|security code|m[aã]\s*x[aá]c\s*nh[aậ]n|m[aã]|code)"
    r"[^A-Z0-9]{0,20}([A-Z0-9]{4,10})"
)
GENERIC_CODE_RE = re.compile(r"\b\d{4,8}\b")
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def html_to_text(value: str) -> str:
    without_tags = TAG_RE.sub(" ", value or "")
    unescaped = html.unescape(without_tags)
    return WHITESPACE_RE.sub(" ", unescaped).strip()


def extract_text_parts(message: Message) -> tuple[str, str]:
    text_body = ""
    html_body = ""

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if content_type == "text/plain" and not text_body:
                text_body = decoded
            elif content_type == "text/html" and not html_body:
                html_body = decoded
    else:
        payload = message.get_payload(decode=True) or b""
        charset = message.get_content_charset() or "utf-8"
        decoded = payload.decode(charset, errors="replace")
        if message.get_content_type() == "text/html":
            html_body = decoded
        else:
            text_body = decoded

    if not text_body and html_body:
        text_body = html_to_text(html_body)

    return text_body.strip(), html_body.strip()


def extract_recipient(message: Message, domain: str, central_mailbox: str) -> str | None:
    candidates: list[str] = []
    domain_suffix = f"@{domain.lower()}"
    central_normalized = normalize_address(central_mailbox)

    for header in RECIPIENT_HEADERS:
        values = message.get_all(header, [])
        for _display_name, addr in getaddresses(values):
            normalized = normalize_address(addr)
            if normalized.endswith(domain_suffix):
                candidates.append(normalized)

    for candidate in candidates:
        if candidate != central_normalized:
            return candidate
    return candidates[0] if candidates else None


def extract_links(text_body: str, html_body: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for source in (text_body, html_body):
        for url in URL_RE.findall(source or ""):
            normalized = url.rstrip(".,)")
            if normalized in seen:
                continue
            seen.add(normalized)
            link_type = "generic"
            lowered = normalized.lower()
            if any(keyword in lowered for keyword in ("verify", "verification", "confirm")):
                link_type = "verify"
            elif "reset" in lowered:
                link_type = "reset_password"
            links.append({"url": normalized, "type": link_type})
    return links


def extract_otps(text_body: str, html_body: str) -> list[dict[str, str]]:
    combined = "\n".join(part for part in (text_body, html_body) if part)
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    for match in OTP_CONTEXT_RE.finditer(combined):
        code = match.group(1)
        if code in seen:
            continue
        seen.add(code)
        context = combined[max(0, match.start() - 32): match.end() + 32].strip()
        found.append({"code": code, "context": context})

    if not found:
        for match in GENERIC_CODE_RE.finditer(combined):
            code = match.group(0)
            if code in seen:
                continue
            seen.add(code)
            context = combined[max(0, match.start() - 24): match.end() + 24].strip()
            found.append({"code": code, "context": context})
            if len(found) >= 3:
                break

    return found


def extract_snippet(text_body: str) -> str:
    snippet = WHITESPACE_RE.sub(" ", (text_body or "").replace("\n", " ")).strip()
    return snippet[:180]


def parse_received_at(message: Message) -> str:
    raw_date = message.get("Date")
    if not raw_date:
        return utc_now().isoformat()
    try:
        return parsedate_to_datetime(raw_date).astimezone().isoformat()
    except Exception:
        return utc_now().isoformat()


def collect_headers(message: Message) -> dict[str, Any]:
    return {
        "subject": message.get("Subject", ""),
        "from": message.get("From", ""),
        "to": message.get("To", ""),
        "cc": message.get("Cc", ""),
        "message_id": message.get("Message-Id", ""),
        "delivered_to": message.get("Delivered-To", ""),
        "x_original_to": message.get("X-Original-To", ""),
    }
