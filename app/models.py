from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(48), index=True)
    account_code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    sessions: Mapped[list["SessionRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memberships: Mapped[list["GroupMembership"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    created_groups: Mapped[list["Group"]] = relationship(back_populates="creator")


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="sessions")


class Group(TimestampMixin, Base):
    __tablename__ = "chat_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(80))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    creator: Mapped[User] = relationship(back_populates="created_groups")
    memberships: Mapped[list["GroupMembership"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_membership"),
        UniqueConstraint("group_id", "alias", name="uq_group_alias"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("chat_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(48), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    group: Mapped[Group] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")
    messages: Mapped[list["Message"]] = relationship(back_populates="membership", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("chat_groups.id", ondelete="CASCADE"), index=True)
    membership_id: Mapped[int] = mapped_column(ForeignKey("group_memberships.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    group: Mapped[Group] = relationship(back_populates="messages")
    membership: Mapped[GroupMembership] = relationship(back_populates="messages")