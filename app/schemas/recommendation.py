"""Recommendation output schema."""

from __future__ import annotations

from pydantic import BaseModel

from app.services.recommendation_engine import Recommendation


class RecommendationOut(BaseModel):
    media_type: str
    title: str
    creator: str | None
    release_year: int | None
    genres: list[str]
    image_url: str | None
    origin: str
    source: str
    external_id: str | None
    external_url: str | None
    match_percent: int
    reasons: list[str]

    @classmethod
    def from_recommendation(cls, rec: Recommendation) -> "RecommendationOut":
        item = rec.item
        return cls(
            media_type=item.media_type,
            title=item.title,
            creator=item.creator,
            release_year=item.release_year,
            genres=item.genres,
            image_url=item.image_url,
            origin=item.origin,
            source=item.source,
            external_id=item.external_id,
            external_url=item.external_url,
            match_percent=rec.match_percent,
            reasons=rec.reasons,
        )


class RecommendationListOut(BaseModel):
    cold_start: bool
    library_size: int
    online_used: bool
    online_errors: list[str]
    recommendations: list[RecommendationOut]
