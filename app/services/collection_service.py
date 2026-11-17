"""Collection management: create, rename, delete and organise items."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models import Collection, Item, User
from app.schemas.collection import CollectionIn


def list_collections(db: Session, user: User) -> list[Collection]:
    stmt = (
        select(Collection)
        .where(Collection.user_id == user.id)
        .options(selectinload(Collection.items))
        .order_by(func.lower(Collection.name))
    )
    return list(db.scalars(stmt).all())


def get_collection(db: Session, user: User, collection_id: int) -> Collection:
    collection = db.get(Collection, collection_id)
    if collection is None or collection.user_id != user.id:
        raise NotFoundError("That collection doesn't exist or doesn't belong to you.")
    return collection


def _ensure_unique_name(db: Session, user: User, name: str, exclude_id: int | None = None) -> None:
    stmt = select(Collection.id).where(Collection.user_id == user.id, func.lower(Collection.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Collection.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise ConflictError(f"You already have a collection called “{name}”.", field="name")


def create_collection(db: Session, user: User, data: CollectionIn) -> Collection:
    _ensure_unique_name(db, user, data.name)
    collection = Collection(user_id=user.id, name=data.name, description=data.description)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def update_collection(db: Session, user: User, collection_id: int, data: CollectionIn) -> Collection:
    collection = get_collection(db, user, collection_id)
    _ensure_unique_name(db, user, data.name, exclude_id=collection.id)
    collection.name = data.name
    collection.description = data.description
    db.commit()
    db.refresh(collection)
    return collection


def delete_collection(db: Session, user: User, collection_id: int) -> str:
    """Delete a collection. Items stay in the library; only the grouping is removed."""
    collection = get_collection(db, user, collection_id)
    name = collection.name
    db.delete(collection)
    db.commit()
    return name


def add_items(db: Session, user: User, collection_id: int, item_ids: Iterable[int]) -> int:
    collection = get_collection(db, user, collection_id)
    ids = {int(i) for i in item_ids}
    if not ids:
        return 0
    current = {item.id for item in collection.items}
    new_items = db.scalars(select(Item).where(Item.user_id == user.id, Item.id.in_(ids - current))).all()
    collection.items.extend(new_items)
    db.commit()
    return len(new_items)


def remove_item(db: Session, user: User, collection_id: int, item_id: int) -> str:
    collection = get_collection(db, user, collection_id)
    for item in list(collection.items):
        if item.id == item_id:
            collection.items.remove(item)
            db.commit()
            return item.title
    raise NotFoundError("That item isn't in this collection.")


def items_not_in_collection(db: Session, user: User, collection: Collection) -> list[Item]:
    member_ids = [item.id for item in collection.items]
    stmt = select(Item).where(Item.user_id == user.id)
    if member_ids:
        stmt = stmt.where(Item.id.not_in(member_ids))
    return list(db.scalars(stmt.order_by(func.lower(Item.title))).all())
