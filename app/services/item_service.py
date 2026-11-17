"""Item management: create, read, update, delete, search, filter and tagging."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import String, delete, func, literal, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import ITEMS_PER_PAGE, MAX_KEYWORDS_PER_ITEM, MEDIA_TYPE_KEYS, SORT_OPTIONS, STATUS_KEYS
from app.core.errors import NotFoundError
from app.models import Collection, Item, Tag, User, item_tags
from app.schemas.item import ItemIn
from app.services.text_utils import extract_keywords, merge_unique, to_csv

LIKE_ESCAPE = "\\"


def _like_pattern(value: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# --- Filtering -----------------------------------------------------------------
@dataclass
class ItemFilters:
    q: str = ""
    media_type: str = ""
    tag: str = ""
    genre: str = ""
    status: str = ""
    favourites_only: bool = False
    min_rating: int | None = None
    collection_id: int | None = None
    sort: str = "recent"
    page: int = 1
    per_page: int = ITEMS_PER_PAGE

    @classmethod
    def from_params(
        cls,
        *,
        q: str = "",
        media_type: str = "",
        tag: str = "",
        genre: str = "",
        status: str = "",
        favourites: str = "",
        rating: str = "",
        sort: str = "",
        page: str = "",
        collection_id: int | None = None,
        per_page: int = ITEMS_PER_PAGE,
    ) -> "ItemFilters":
        """Build filters from raw query parameters, discarding invalid values."""
        min_rating = int(rating) if rating.strip().isdigit() and 1 <= int(rating) <= 5 else None
        page_number = int(page) if page.strip().isdigit() and int(page) > 0 else 1
        return cls(
            q=q.strip()[:100],
            media_type=media_type if media_type in MEDIA_TYPE_KEYS else "",
            tag=tag.strip().lower()[:40],
            genre=genre.strip()[:60],
            status=status if status in STATUS_KEYS else "",
            favourites_only=favourites.strip().lower() in {"1", "true", "on", "yes"},
            min_rating=min_rating,
            collection_id=collection_id,
            sort=sort if sort in SORT_OPTIONS else "recent",
            page=page_number,
            per_page=per_page,
        )

    def as_query(self) -> dict[str, Any]:
        """Current filters as URL query parameters (used for links and pagination)."""
        return {
            "q": self.q,
            "type": self.media_type,
            "tag": self.tag,
            "genre": self.genre,
            "status": self.status,
            "favourites": "1" if self.favourites_only else "",
            "rating": self.min_rating or "",
            "sort": self.sort if self.sort != "recent" else "",
        }

    @property
    def has_filters(self) -> bool:
        return any([self.q, self.media_type, self.tag, self.genre, self.status, self.favourites_only, self.min_rating])


@dataclass
class ItemPage:
    items: list[Item]
    total: int
    page: int
    per_page: int
    pages: int = field(init=False)

    def __post_init__(self) -> None:
        self.pages = max(1, math.ceil(self.total / self.per_page)) if self.per_page else 1


def _filtered_statement(user: User, filters: ItemFilters):
    stmt = select(Item).where(Item.user_id == user.id)

    if filters.q:
        pattern = _like_pattern(filters.q)
        stmt = stmt.where(
            or_(
                Item.title.ilike(pattern, escape=LIKE_ESCAPE),
                Item.creator.ilike(pattern, escape=LIKE_ESCAPE),
                Item.description.ilike(pattern, escape=LIKE_ESCAPE),
                Item.notes.ilike(pattern, escape=LIKE_ESCAPE),
                Item.genres.ilike(pattern, escape=LIKE_ESCAPE),
                Item.tags.any(Tag.name.ilike(pattern, escape=LIKE_ESCAPE)),
            )
        )
    if filters.media_type:
        stmt = stmt.where(Item.media_type == filters.media_type)
    if filters.tag:
        stmt = stmt.where(Item.tags.any(Tag.name == filters.tag))
    if filters.genre:
        # Genres are stored as "A,B,C"; wrap in commas to match whole entries only.
        wrapped = literal(",", String) + func.lower(Item.genres, type_=String) + literal(",", String)
        escaped = _like_pattern(filters.genre.lower())[1:-1]
        stmt = stmt.where(wrapped.like(f"%,{escaped},%", escape=LIKE_ESCAPE))
    if filters.status:
        stmt = stmt.where(Item.status == filters.status)
    if filters.favourites_only:
        stmt = stmt.where(Item.is_favourite.is_(True))
    if filters.min_rating:
        stmt = stmt.where(Item.rating >= filters.min_rating)
    if filters.collection_id is not None:
        stmt = stmt.where(Item.collections.any(Collection.id == filters.collection_id))
    return stmt


_SORTS = {
    "recent": (Item.created_at.desc(), Item.id.desc()),
    "title": (func.lower(Item.title).asc(), Item.id.asc()),
    "rating": (Item.rating.desc().nulls_last(), Item.created_at.desc()),
    "year": (Item.release_year.desc().nulls_last(), func.lower(Item.title).asc()),
}


def list_items(db: Session, user: User, filters: ItemFilters) -> ItemPage:
    """Search, filter, sort and paginate the user's items."""
    stmt = _filtered_statement(user, filters)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    page = min(filters.page, max(1, math.ceil(total / filters.per_page))) if total else 1
    stmt = (
        stmt.options(selectinload(Item.tags))
        .order_by(*_SORTS.get(filters.sort, _SORTS["recent"]))
        .offset((page - 1) * filters.per_page)
        .limit(filters.per_page)
    )
    return ItemPage(items=list(db.scalars(stmt).all()), total=total, page=page, per_page=filters.per_page)


def all_items(db: Session, user: User) -> list[Item]:
    stmt = (
        select(Item)
        .where(Item.user_id == user.id)
        .options(selectinload(Item.tags))
        .order_by(Item.media_type, func.lower(Item.title))
    )
    return list(db.scalars(stmt).all())


# --- CRUD ------------------------------------------------------------------------
def get_item(db: Session, user: User, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None or item.user_id != user.id:
        raise NotFoundError("That item doesn't exist or isn't in your library.")
    return item


def get_or_create_tags(db: Session, user: User, names: Iterable[str]) -> list[Tag]:
    names = [n for n in dict.fromkeys(names) if n]
    if not names:
        return []
    existing = {t.name: t for t in db.scalars(select(Tag).where(Tag.user_id == user.id, Tag.name.in_(names)))}
    tags: list[Tag] = []
    for name in names:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(user_id=user.id, name=name)
            db.add(tag)
            existing[name] = tag
        tags.append(tag)
    return tags


def prune_unused_tags(db: Session, user: User) -> None:
    db.execute(delete(Tag).where(Tag.user_id == user.id, ~Tag.items.any()).execution_options(synchronize_session=False))
    db.commit()


def owned_collections(db: Session, user: User, collection_ids: Iterable[int]) -> list[Collection]:
    ids = list({int(cid) for cid in collection_ids})
    if not ids:
        return []
    stmt = select(Collection).where(Collection.user_id == user.id, Collection.id.in_(ids))
    return list(db.scalars(stmt).all())


def _apply_data(db: Session, user: User, item: Item, data: ItemIn) -> None:
    item.media_type = data.media_type
    item.title = data.title
    item.creator = data.creator
    item.release_year = data.release_year
    item.description = data.description
    item.genres = to_csv(data.genres)
    item.keywords = to_csv(
        merge_unique(data.keywords, extract_keywords(data.title, data.description), limit=MAX_KEYWORDS_PER_ITEM)
    )
    item.image_url = data.image_url
    item.external_source = data.external_source
    item.external_id = data.external_id
    item.external_url = data.external_url
    item.rating = data.rating
    item.is_favourite = data.is_favourite
    item.status = data.status
    item.notes = data.notes
    item.tags = get_or_create_tags(db, user, data.tags)


def create_item(db: Session, user: User, data: ItemIn, collection_ids: Iterable[int] = ()) -> Item:
    item = Item(user_id=user.id)
    _apply_data(db, user, item, data)
    item.collections = owned_collections(db, user, collection_ids)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(
    db: Session, user: User, item_id: int, data: ItemIn, collection_ids: Iterable[int] | None = None
) -> Item:
    item = get_item(db, user, item_id)
    _apply_data(db, user, item, data)
    if collection_ids is not None:
        item.collections = owned_collections(db, user, collection_ids)
    db.commit()
    prune_unused_tags(db, user)
    db.refresh(item)
    return item


def delete_item(db: Session, user: User, item_id: int) -> str:
    item = get_item(db, user, item_id)
    title = item.title
    db.delete(item)
    db.commit()
    prune_unused_tags(db, user)
    return title


def toggle_favourite(db: Session, user: User, item_id: int) -> Item:
    item = get_item(db, user, item_id)
    item.is_favourite = not item.is_favourite
    db.commit()
    return item


def set_item_collections(db: Session, user: User, item_id: int, collection_ids: Iterable[int]) -> Item:
    item = get_item(db, user, item_id)
    item.collections = owned_collections(db, user, collection_ids)
    db.commit()
    db.refresh(item)
    return item


def find_duplicate(db: Session, user: User, media_type: str, title: str, external_id: str | None = None) -> Item | None:
    """Return an existing item that looks like the same title (used to avoid duplicates)."""
    stmt = select(Item).where(Item.user_id == user.id, Item.media_type == media_type)
    if external_id:
        match = db.scalar(stmt.where(Item.external_id == external_id))
        if match:
            return match
    return db.scalar(stmt.where(func.lower(Item.title) == title.strip().lower()))


# --- Facets used by filters and the dashboard ------------------------------------
def type_counts(db: Session, user: User) -> dict[str, int]:
    rows = db.execute(
        select(Item.media_type, func.count(Item.id)).where(Item.user_id == user.id).group_by(Item.media_type)
    ).all()
    counts = {key: 0 for key in MEDIA_TYPE_KEYS}
    counts.update({media_type: count for media_type, count in rows})
    return counts


def tag_counts(db: Session, user: User) -> list[tuple[str, int]]:
    stmt = (
        select(Tag.name, func.count(item_tags.c.item_id))
        .join(item_tags, item_tags.c.tag_id == Tag.id)
        .where(Tag.user_id == user.id)
        .group_by(Tag.name)
        .order_by(func.count(item_tags.c.item_id).desc(), Tag.name)
    )
    return [(name, count) for name, count in db.execute(stmt).all()]


def genre_counts(db: Session, user: User) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for (genres,) in db.execute(select(Item.genres).where(Item.user_id == user.id)).all():
        counter.update(g.strip() for g in (genres or "").split(",") if g.strip())
    return sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))
