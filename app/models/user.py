"""User account model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import utcnow

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.item import Item
    from app.models.tag import Tag


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(80))
    bio: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    items: Mapped[list["Item"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    collections: Mapped[list["Collection"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    tags: Mapped[list["Tag"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def name(self) -> str:
        """Friendly name shown in the interface."""
        return self.display_name or self.username

    @property
    def initials(self) -> str:
        parts = self.name.split()
        letters = "".join(p[0] for p in parts[:2]) if parts else self.username[:2]
        return letters.upper()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User id={self.id} username={self.username!r}>"
