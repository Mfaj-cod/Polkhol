from __future__ import annotations

import random
import secrets
from string import ascii_uppercase, digits

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GroupMembership, User


USERNAME_ADJECTIVES = [
    "Silent",
    "Velvet",
    "Midnight",
    "Solar",
    "Hidden",
    "Electric",
    "Neon",
    "Obsidian",
    "Whisper",
    "Cobalt",
]
USERNAME_NOUNS = [
    "Voyager",
    "Signal",
    "Lantern",
    "Pulse",
    "Cipher",
    "Comet",
    "Drift",
    "Fable",
    "Orbit",
    "Echo",
]
ALIAS_ADJECTIVES = [
    "Quiet",
    "Shaded",
    "Amber",
    "Ghost",
    "Silver",
    "Lunar",
    "Nova",
    "Mellow",
    "Crimson",
    "Ivory",
]
ALIAS_NOUNS = [
    "Fox",
    "Harbor",
    "Spark",
    "Dawn",
    "River",
    "Verse",
    "Glider",
    "Flame",
    "Comet",
    "Path",
]
CODE_ALPHABET = "".join(character for character in ascii_uppercase + digits if character not in {"0", "1", "I", "O"})


def make_random_username() -> str:
    return f"{random.choice(USERNAME_ADJECTIVES)} {random.choice(USERNAME_NOUNS)} {random.randint(100, 999)}"


def make_account_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        exists = db.scalar(select(User.id).where(User.account_code == code))
        if exists is None:
            return code
    raise RuntimeError("Unable to generate a unique account code.")


def make_group_alias(db: Session, group_id: int) -> str:
    for _ in range(40):
        alias = f"{random.choice(ALIAS_ADJECTIVES)} {random.choice(ALIAS_NOUNS)} {random.randint(10, 99)}"
        exists = db.scalar(
            select(GroupMembership.id)
            .where(GroupMembership.group_id == group_id)
            .where(GroupMembership.alias == alias)
        )
        if exists is None:
            return alias
    raise RuntimeError("Unable to generate a unique group alias.")


