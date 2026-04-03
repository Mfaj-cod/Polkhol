from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import SessionRecord, User


password_hasher = PasswordHasher()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User, settings: Settings) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    session = SessionRecord(user_id=user.id, token_hash=hash_token(token), expires_at=expires_at)
    db.add(session)
    db.commit()
    return token


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return

    session = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == hash_token(token)))
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()


def sync_admin_status(db: Session, user: User, settings: Settings) -> None:
    should_be_admin = bool(settings.admin_email) and user.email == settings.admin_email
    if user.is_admin != should_be_admin:
        user.is_admin = should_be_admin
        db.commit()


def get_user_from_token(db: Session, token: str | None, settings: Settings) -> User | None:
    if not token:
        return None

    now = datetime.now(timezone.utc)
    session = db.scalar(
        select(SessionRecord)
        .where(SessionRecord.token_hash == hash_token(token))
        .where(SessionRecord.revoked_at.is_(None))
        .where(SessionRecord.expires_at > now)
    )
    if session is None:
        return None

    user = session.user
    sync_admin_status(db, user, settings)
    return user


