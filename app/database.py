from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def init_database(database_url: str) -> None:
    global engine, SessionLocal

    if engine is not None:
        engine.dispose()

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    from app.models import Base

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database has not been initialized.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()