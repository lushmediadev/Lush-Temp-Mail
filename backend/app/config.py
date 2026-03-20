from __future__ import annotations

import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.root_dir = Path(__file__).resolve().parents[2]
        self.frontend_dir = self.root_dir
        default_data_dir = self.root_dir / "data"
        self.data_dir = Path(os.getenv("TEMPMAIL_DATA_DIR", default_data_dir))
        self.database_path = Path(os.getenv("TEMPMAIL_DB_PATH", self.data_dir / "lush_temp_mail.db"))
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        self.session_cookie_name = os.getenv("SESSION_COOKIE_NAME", "lush_temp_mail_session")
        self.session_ttl_hours = int(os.getenv("SESSION_TTL_HOURS", "168"))
        self.app_base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8010")
        self.public_domain = os.getenv("TEMPMAIL_PUBLIC_DOMAIN", "lush.congmail.top")
        self.mail_domain = os.getenv("TEMPMAIL_MAIL_DOMAIN", "congmail.top")
        self.central_mailbox = os.getenv("CENTRAL_MAILBOX", f"contact@{self.mail_domain}")
        self.imap_host = os.getenv("IMAP_HOST", "mail.congmail.top")
        self.imap_port = int(os.getenv("IMAP_PORT", "993"))
        self.imap_username = os.getenv("IMAP_USERNAME", self.central_mailbox)
        self.imap_password = os.getenv("IMAP_PASSWORD", "")
        self.smtp_host = os.getenv("SMTP_HOST", self.imap_host)
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", self.imap_username)
        self.smtp_password = os.getenv("SMTP_PASSWORD", self.imap_password)
        self.smtp_security = os.getenv("SMTP_SECURITY", "starttls").strip().lower()
        self.smtp_from_address = os.getenv("SMTP_FROM_ADDRESS", self.central_mailbox)
        self.smtp_from_name = os.getenv("SMTP_FROM_NAME", "LushMail")
        self.sync_interval_s = int(os.getenv("MAIL_SYNC_INTERVAL_S", "4"))
        self.sync_enabled = _env_bool("MAIL_SYNC_ENABLED", True)
        self.default_alias_hours = int(os.getenv("DEFAULT_ALIAS_HOURS", "1440"))
        self.message_retention_days = int(os.getenv("MESSAGE_RETENTION_DAYS", "60"))
        self.secure_cookie = _env_bool("SECURE_COOKIE", False)
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
