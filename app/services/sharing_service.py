"""Public, read-only share links for collections.

A shared collection gets a random 24-character URL-safe token
(``secrets.token_urlsafe(18)``, ~144 bits of entropy), so links cannot be
guessed. Turning sharing off deletes the token, which immediately revokes the
old link; sharing again issues a brand-new token.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.core.security import generate_token
from app.models import Collection, Item, User
from app.models.base import utcnow
from app.services.collection_service import get_collection

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def enable_sharing(db: Session, user: User, collection_id: int) -> Collection:
    collection = get_collection(db, user, collection_id)
    if not collection.share_token:
        collection.share_token = generate_token(18)
        collection.shared_at = utcnow()
        db.commit()
        db.refresh(collection)
    return collection


def disable_sharing(db: Session, user: User, collection_id: int) -> Collection:
    collection = get_collection(db, user, collection_id)
    collection.share_token = None
    collection.shared_at = None
    db.commit()
    db.refresh(collection)
    return collection


def get_shared_collection(db: Session, token: str) -> Collection:
    """Look up a collection by its public token (no authentication)."""
    not_found = NotFoundError("This shared collection link is invalid or sharing has been turned off.")
    if not _TOKEN_RE.fullmatch(token or ""):
        raise not_found
    stmt = (
        select(Collection)
        .where(Collection.share_token == token)
        .options(selectinload(Collection.items).selectinload(Item.tags), selectinload(Collection.owner))
    )
    collection = db.scalar(stmt)
    if collection is None:
        raise not_found
    return collection


def sorted_items(collection: Collection) -> list[Item]:
    return sorted(collection.items, key=lambda i: (i.media_type, i.title.lower()))
