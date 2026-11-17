"""Many-to-many association tables."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table

from app.database import Base
from app.models.base import utcnow

# An item can carry many tags; a tag can label many items.
item_tags = Table(
    "item_tags",
    Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

# An item can belong to many collections; a collection holds many items.
collection_items = Table(
    "collection_items",
    Base.metadata,
    Column("collection_id", Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("added_at", DateTime, default=utcnow, nullable=False),
)
