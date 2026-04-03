from __future__ import annotations

import os
import secrets
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    app_name: str = "PolKhol"
    database_url: str = "sqlite:///./polkhol.db"
    secret_key: str = secrets.token_urlsafe(32)
    admin_email: str = ""
    session_cookie_name: str = "polkhol_session"
    csrf_cookie_name: str = "polkhol_csrf"
    session_ttl_hours: int = 24 * 14
    max_message_length: int = 2000

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "PolKhol"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./polkhol.db"),
            secret_key=os.getenv("SECRET_KEY", secrets.token_urlsafe(32)),
            admin_email=os.getenv("ADMIN_EMAIL", "").strip().lower(),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "polkhol_session"),
            csrf_cookie_name=os.getenv("CSRF_COOKIE_NAME", "polkhol_csrf"),
            session_ttl_hours=int(os.getenv("SESSION_TTL_HOURS", str(24 * 14))),
            max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "2000")),
        )