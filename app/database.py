"""Database engine, session factory and initialisation helpers (SQLAlchemy 2.0)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base class for all Curio ORM models."""


def _ensure_sqlite_directory(database_url: str) -> None:
    """Create the parent folder of a file-based SQLite database if needed."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return
    path = database_url[len(prefix):]
    if not path or path == ":memory:":
        return
    Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def build_engine(database_url: str) -> Engine:
    """Create an engine; SQLite connections get foreign-key enforcement."""
    is_sqlite = database_url.startswith("sqlite")
    _ensure_sqlite_directory(database_url)
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    new_engine = create_engine(database_url, connect_args=connect_args, future=True)

    if is_sqlite:

        @event.listens_for(new_engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:  # pragma: no cover - driver hook
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return new_engine


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind: Engine | None = None) -> None:
    """Create all tables that do not yet exist."""
    from app import models  # noqa: F401  (import registers the models on Base.metadata)

    Base.metadata.create_all(bind=bind or engine)
