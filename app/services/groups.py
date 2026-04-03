from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Group, GroupMembership, Message, User
from app.services.identity import make_group_alias


@dataclass(slots=True)
class DashboardGroup:
    id: int
    title: str
    member_count: int
    your_alias: str
    can_manage: bool
    last_message_alias: str | None
    last_message_body: str | None
    last_message_at: str | None


@dataclass(slots=True)
class RoomMessage:
    alias: str
    body: str
    created_at: str


@dataclass(slots=True)
class RoomData:
    group: Group
    membership: GroupMembership
    aliases: list[str]
    messages: list[RoomMessage]


def _format_timestamp(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%b %d, %Y %I:%M %p")


def list_groups_for_user(db: Session, user: User) -> list[DashboardGroup]:
    memberships = db.scalars(
        select(GroupMembership)
        .where(GroupMembership.user_id == user.id)
        .options(joinedload(GroupMembership.group))
        .order_by(GroupMembership.created_at.desc())
    ).all()

    groups: list[DashboardGroup] = []
    for membership in memberships:
        group = membership.group
        member_count = db.scalar(select(func.count(GroupMembership.id)).where(GroupMembership.group_id == group.id)) or 0
        last_message = db.execute(
            select(Message, GroupMembership.alias)
            .join(GroupMembership, GroupMembership.id == Message.membership_id)
            .where(Message.group_id == group.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        ).first()
        groups.append(
            DashboardGroup(
                id=group.id,
                title=group.title,
                member_count=member_count,
                your_alias=membership.alias,
                can_manage=user.is_admin or group.creator_id == user.id,
                last_message_alias=last_message[1] if last_message else None,
                last_message_body=last_message[0].body if last_message else None,
                last_message_at=_format_timestamp(last_message[0].created_at) if last_message else None,
            )
        )
    return groups


def resolve_users_by_codes(db: Session, member_codes: list[str], exclude_user_id: int | None = None) -> list[User]:
    unique_codes = sorted({code.strip().upper() for code in member_codes if code.strip()})
    if not unique_codes:
        return []

    statement = select(User).where(User.account_code.in_(unique_codes))
    if exclude_user_id is not None:
        statement = statement.where(User.id != exclude_user_id)
    return db.scalars(statement).all()


def create_group(db: Session, creator: User, title: str, member_codes: list[str]) -> Group:
    cleaned_title = title.strip()
    if not cleaned_title:
        raise ValueError("Group title is required.")
    if len(cleaned_title) > 80:
        raise ValueError("Group title must be 80 characters or fewer.")

    group = Group(title=cleaned_title, creator_id=creator.id)
    db.add(group)
    db.flush()

    creator_membership = GroupMembership(
        group_id=group.id,
        user_id=creator.id,
        alias=make_group_alias(db, group.id),
    )
    db.add(creator_membership)
    db.flush()

    additional_users = resolve_users_by_codes(db, member_codes, exclude_user_id=creator.id)
    existing_ids = {creator.id}
    for user in additional_users:
        if user.id in existing_ids:
            continue
        existing_ids.add(user.id)
        db.add(
            GroupMembership(
                group_id=group.id,
                user_id=user.id,
                alias=make_group_alias(db, group.id),
            )
        )
        db.flush()

    db.commit()
    db.refresh(group)
    return group


def add_members_to_group(db: Session, actor: User, group_id: int, member_codes: list[str]) -> list[GroupMembership]:
    group = db.scalar(select(Group).where(Group.id == group_id))
    if group is None:
        raise ValueError("Group not found.")
    if not (actor.is_admin or group.creator_id == actor.id):
        raise PermissionError("Only the creator can add members.")

    users = resolve_users_by_codes(db, member_codes, exclude_user_id=None)
    if not users:
        return []

    existing_ids = {
        user_id
        for (user_id,) in db.execute(select(GroupMembership.user_id).where(GroupMembership.group_id == group_id)).all()
    }

    added: list[GroupMembership] = []
    for user in users:
        if user.id in existing_ids:
            continue
        membership = GroupMembership(
            group_id=group_id,
            user_id=user.id,
            alias=make_group_alias(db, group_id),
        )
        db.add(membership)
        db.flush()
        added.append(membership)

    db.commit()
    return added


def get_room_data(db: Session, group_id: int, user: User) -> RoomData | None:
    membership = db.scalar(
        select(GroupMembership)
        .where(GroupMembership.group_id == group_id)
        .where(GroupMembership.user_id == user.id)
        .options(joinedload(GroupMembership.group))
    )
    if membership is None:
        return None

    aliases = db.scalars(
        select(GroupMembership.alias)
        .where(GroupMembership.group_id == group_id)
        .order_by(GroupMembership.alias.asc())
    ).all()
    recent_rows = db.execute(
        select(Message, GroupMembership.alias)
        .join(GroupMembership, GroupMembership.id == Message.membership_id)
        .where(Message.group_id == group_id)
        .order_by(Message.created_at.desc())
        .limit(200)
    ).all()
    messages = [
        RoomMessage(alias=alias, body=message.body, created_at=_format_timestamp(message.created_at))
        for message, alias in reversed(recent_rows)
    ]
    return RoomData(group=membership.group, membership=membership, aliases=aliases, messages=messages)


def search_users(db: Session, query: str, actor: User, group_id: int | None = None) -> list[dict[str, str]]:
    cleaned_query = query.strip()
    if len(cleaned_query) < 2:
        return []

    statement = (
        select(User)
        .where(User.id != actor.id)
        .where(
            or_(
                User.username.ilike(f"%{cleaned_query}%"),
                User.account_code.ilike(f"%{cleaned_query.upper()}%"),
            )
        )
        .order_by(User.username.asc(), User.account_code.asc())
        .limit(8)
    )
    users = db.scalars(statement).all()

    excluded_user_ids: set[int] = set()
    if group_id is not None:
        excluded_user_ids = {
            user_id
            for (user_id,) in db.execute(select(GroupMembership.user_id).where(GroupMembership.group_id == group_id)).all()
        }

    return [
        {"username": user.username, "account_code": user.account_code}
        for user in users
        if user.id not in excluded_user_ids
    ]


def get_group_aliases(db: Session, group_id: int) -> list[str]:
    return db.scalars(
        select(GroupMembership.alias)
        .where(GroupMembership.group_id == group_id)
        .order_by(GroupMembership.alias.asc())
    ).all()


def create_message(db: Session, membership: GroupMembership, body: str) -> Message:
    message = Message(group_id=membership.group_id, membership_id=membership.id, body=body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_membership(db: Session, group_id: int, user_id: int) -> GroupMembership | None:
    return db.scalar(
        select(GroupMembership)
        .where(GroupMembership.group_id == group_id)
        .where(GroupMembership.user_id == user_id)
    )