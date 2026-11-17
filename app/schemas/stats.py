"""Dashboard statistics JSON schema."""

from __future__ import annotations

from pydantic import BaseModel

from app.services.stats_service import DashboardStats


class NamedCount(BaseModel):
    name: str
    count: int


class RecentItem(BaseModel):
    id: int
    title: str
    media_type: str
    rating: int | None
    is_favourite: bool


class DashboardStatsOut(BaseModel):
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
    top_genres: list[NamedCount]
    top_tags: list[NamedCount]
    recent_items: list[RecentItem]

    @classmethod
    def from_stats(cls, stats: DashboardStats) -> "DashboardStatsOut":
        return cls(
            total_items=stats.total_items,
            type_counts=stats.type_counts,
            favourites_count=stats.favourites_count,
            rated_count=stats.rated_count,
            average_rating=stats.average_rating,
            collections_count=stats.collections_count,
            shared_collections_count=stats.shared_collections_count,
            tags_count=stats.tags_count,
            added_last_30_days=stats.added_last_30_days,
            status_counts=stats.status_counts,
            rating_distribution=stats.rating_distribution,
            top_genres=[NamedCount(name=n, count=c) for n, c in stats.top_genres],
            top_tags=[NamedCount(name=n, count=c) for n, c in stats.top_tags],
            recent_items=[
                RecentItem(id=i.id, title=i.title, media_type=i.media_type, rating=i.rating, is_favourite=i.is_favourite)
                for i in stats.recent_items
            ],
        )
