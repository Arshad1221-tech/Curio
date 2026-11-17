"""User-defined collection model with optional public share link."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.associations import collection_items
from app.models.base import utcnow

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.user import User


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_collections_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # A non-null, unguessable token means the collection is publicly shared.
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    shared_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="collections")
    items: Mapped[list["Item"]] = relationship(
        secondary=collection_items, back_populates="collections", order_by="Item.title"
    )

    @property
    def is_shared(self) -> bool:
        return self.share_token is not None

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def cover_images(self) -> list[str]:
        """Up to four cover images for a collection mosaic."""
        return [item.image_url for item in self.items if item.image_url][:4]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Collection id={self.id} name={self.name!r}>"
