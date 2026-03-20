from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta


LOCAL_PART_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,62}[a-z0-9])?$")


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def iso_in_hours(hours: int) -> str:
    return (utc_now() + timedelta(hours=hours)).isoformat()


def iso_days_ago(days: int) -> str:
    return (utc_now() - timedelta(days=days)).isoformat()


def normalize_address(address: str) -> str:
    return address.strip().lower()


def split_address(address: str) -> tuple[str, str]:
    normalized = normalize_address(address)
    local_part, domain = normalized.split("@", 1)
    return local_part, domain


def is_valid_local_part(local_part: str) -> bool:
    return bool(LOCAL_PART_RE.fullmatch(local_part.strip().lower()))


def random_local_part(length: int = 10) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
