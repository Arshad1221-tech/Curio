"""Personal statistics shown on the dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import STATUS_KEYS
from app.models import Collection, Item, Tag, User
from app.models.base import utcnow
from app.services import item_service


@dataclass
class DashboardStats:
    total_items: int
    type_counts: dict[str, int]
    favourites_count: int
    rated_count: int
    average_rating: float | None
    collections_count: int
    shared_collections_count: int
    tags_count: int
    added_last_30_days: int
    status_counts: dict[str, int]
    rating_distribution: dict[int, int]
    top_genres: list[tuple[str, int]]
    top_tags: list[tuple[str, int]]
    recent_items: list[Item] = field(default_factory=list)
    top_rated: list[Item] = field(default_factory=list)

    @property
    def max_type_count(self) -> int:
        return max(self.type_counts.values(), default=0) or 1

    @property
    def max_genre_count(self) -> int:
        return max((c for _, c in self.top_genres), default=0) or 1

    @property
    def max_rating_count(self) -> int:
        return max(self.rating_distribution.values(), default=0) or 1


def _count(db: Session, stmt) -> int:
    return db.scalar(stmt) or 0


def get_dashboard_stats(db: Session, user: User) -> DashboardStats:
    owned = Item.user_id == user.id

    average = db.scalar(select(func.avg(Item.rating)).where(owned, Item.rating.is_not(None)))
    rating_rows = db.execute(
        select(Item.rating, func.count(Item.id)).where(owned, Item.rating.is_not(None)).group_by(Item.rating)
    ).all()
    status_rows = db.execute(select(Item.status, func.count(Item.id)).where(owned).group_by(Item.status)).all()

    rating_distribution = {star: 0 for star in range(5, 0, -1)}
    rating_distribution.update({int(r): c for r, c in rating_rows if r})
    status_counts = {key: 0 for key in STATUS_KEYS}
    status_counts.update({s: c for s, c in status_rows})

    recent = db.scalars(
        select(Item).where(owned).options(selectinload(Item.tags)).order_by(Item.created_at.desc(), Item.id.desc()).limit(6)
    ).all()
    top_rated = db.scalars(
        select(Item)
        .where(owned, Item.rating.is_not(None))
        .order_by(Item.rating.desc(), Item.is_favourite.desc(), Item.updated_at.desc())
        .limit(5)
    ).all()

    type_counts = item_service.type_counts(db, user)
    return DashboardStats(
        total_items=sum(type_counts.values()),
        type_counts=type_counts,
        favourites_count=_count(db, select(func.count(Item.id)).where(owned, Item.is_favourite.is_(True))),
        rated_count=sum(rating_distribution.values()),
        average_rating=round(float(average), 1) if average is not None else None,
        collections_count=_count(db, select(func.count(Collection.id)).where(Collection.user_id == user.id)),
        shared_collections_count=_count(
            db, select(func.count(Collection.id)).where(Collection.user_id == user.id, Collection.share_token.is_not(None))
        ),
        tags_count=_count(db, select(func.count(Tag.id)).where(Tag.user_id == user.id)),
        added_last_30_days=_count(
            db, select(func.count(Item.id)).where(owned, Item.created_at >= utcnow() - timedelta(days=30))
        ),
        status_counts=status_counts,
        rating_distribution=rating_distribution,
        top_genres=item_service.genre_counts(db, user)[:8],
        top_tags=item_service.tag_counts(db, user)[:10],
        recent_items=list(recent),
        top_rated=list(top_rated),
    )
