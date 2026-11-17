"""Collectable item model (book, movie, TV show, song, album or other interest)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DEFAULT_STATUS, MEDIA_TYPES, SQUARE_ARTWORK_TYPES, STATUSES
from app.database import Base
from app.models.associations import collection_items, item_tags
from app.models.base import utcnow

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.tag import Tag
    from app.models.user import User


def _split_csv(value: str | None) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_items_rating_range"),
        Index("ix_items_user_media_type", "user_id", "media_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    creator: Mapped[str | None] = mapped_column(String(255))
    release_year: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    # Comma-separated lists (normalised by the service layer). Genres and keywords
    # come from metadata APIs or manual input and feed the recommendation engine.
    genres: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    keywords: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000))

    external_source: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(100))
    external_url: Mapped[str | None] = mapped_column(String(1000))

    rating: Mapped[int | None] = mapped_column(Integer)
    is_favourite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=DEFAULT_STATUS, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="items")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=item_tags, back_populates="items", order_by="Tag.name"
    )
    collections: Mapped[list["Collection"]] = relationship(
        secondary=collection_items, back_populates="items", order_by="Collection.name"
    )

    # --- Convenience properties used by templates and services -----------------
    @property
    def genre_list(self) -> list[str]:
        return _split_csv(self.genres)

    @property
    def keyword_list(self) -> list[str]:
        return _split_csv(self.keywords)

    @property
    def tag_names(self) -> list[str]:
        return [tag.name for tag in self.tags]

    @property
    def media_label(self) -> str:
        return MEDIA_TYPES.get(self.media_type, MEDIA_TYPES["other"])["label"]

    @property
    def media_icon(self) -> str:
        return MEDIA_TYPES.get(self.media_type, MEDIA_TYPES["other"])["icon"]

    @property
    def creator_label(self) -> str:
        return MEDIA_TYPES.get(self.media_type, MEDIA_TYPES["other"])["creator"]

    @property
    def status_label(self) -> str:
        return STATUSES.get(self.status, self.status)

    @property
    def has_square_artwork(self) -> bool:
        return self.media_type in SQUARE_ARTWORK_TYPES

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Item id={self.id} type={self.media_type} title={self.title!r}>"
