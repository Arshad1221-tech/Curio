"""Personal tag model. Tags are scoped to a single user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.associations import item_tags

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.user import User


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="tags")
    items: Mapped[list["Item"]] = relationship(secondary=item_tags, back_populates="tags")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Tag id={self.id} name={self.name!r}>"
