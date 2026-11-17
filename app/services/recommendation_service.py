"""Builds the candidate pool and runs the recommendation engine for a user.

Candidate sources
-----------------
* **Curio catalogue** - a bundled list of well-known titles (``app/data/catalogue.json``)
  so recommendations work offline and without API keys.
* **Community** - items in collections that *other* users have chosen to share publicly.
* **Online (optional)** - genre-based discovery results from TMDB, Google Books and
  iTunes, based on the user's strongest genres per media type.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import APP_DIR
from app.core.constants import MAX_KEYWORDS_PER_ITEM
from app.core.errors import CurioError
from app.models import Collection, Item, User, collection_items
from app.schemas.metadata import MetadataResult
from app.services import metadata_service
from app.services.recommendation_engine import (
    ContentItem,
    Recommendation,
    build_profile,
    recommend,
    starter_picks,
    top_preferences,
)
from app.services.text_utils import canonical_genres, display_genre, extract_keywords, merge_unique, normalise_label

logger = logging.getLogger("curio.recommendations")

CATALOGUE_PATH = APP_DIR / "data" / "catalogue.json"
MAX_ONLINE_TYPES = 3
GENRES_PER_TYPE = 2
ONLINE_RESULTS_PER_QUERY = 8


@dataclass
class RecommendationResult:
    recommendations: list[Recommendation]
    cold_start: bool
    library_size: int
    preferences: list[tuple[str, str]] = field(default_factory=list)
    online_requested: bool = False
    online_used: bool = False
    online_errors: list[str] = field(default_factory=list)


def _slug(text: str) -> str:
    return "-".join(normalise_label(text).replace("'", "").split())[:64]


@lru_cache(maxsize=1)
def load_catalogue() -> tuple[ContentItem, ...]:
    """Load and cache the bundled starter catalogue."""
    try:
        raw_entries = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.exception("Could not load the recommendation catalogue at %s", CATALOGUE_PATH)
        return ()
    items: list[ContentItem] = []
    for entry in raw_entries:
        keywords = merge_unique(
            entry.get("keywords", []),
            extract_keywords(entry.get("title"), entry.get("description")),
            limit=MAX_KEYWORDS_PER_ITEM,
        )
        items.append(
            ContentItem(
                media_type=entry["media_type"],
                title=entry["title"],
                creator=entry.get("creator"),
                release_year=entry.get("release_year"),
                description=entry.get("description"),
                genres=list(entry.get("genres", [])),
                keywords=keywords,
                source="catalogue",
                external_id=f"{entry['media_type']}-{_slug(entry['title'])}-{entry.get('release_year', '')}",
                origin="catalogue",
                starter=bool(entry.get("starter")),
            )
        )
    return tuple(items)


def item_to_content(item: Item, origin: str = "library") -> ContentItem:
    return ContentItem(
        media_type=item.media_type,
        title=item.title,
        creator=item.creator,
        release_year=item.release_year,
        description=item.description,
        genres=item.genre_list,
        tags=item.tag_names,
        keywords=item.keyword_list,
        image_url=item.image_url,
        source=item.external_source,
        external_id=item.external_id,
        external_url=item.external_url,
        origin=origin,
        rating=item.rating,
        is_favourite=item.is_favourite,
    )


def metadata_to_content(result: MetadataResult) -> ContentItem:
    return ContentItem(
        media_type=result.media_type,
        title=result.title,
        creator=result.creator,
        release_year=result.release_year,
        description=result.description,
        genres=[display_genre(g) for g in canonical_genres(result.genres)],
        keywords=merge_unique(result.keywords, extract_keywords(result.title, result.description), limit=MAX_KEYWORDS_PER_ITEM),
        image_url=result.image_url,
        source=result.source,
        external_id=result.external_id,
        external_url=result.external_url,
        origin="online",
    )


def library_content(db: Session, user: User) -> list[ContentItem]:
    stmt = select(Item).where(Item.user_id == user.id).options(selectinload(Item.tags))
    return [item_to_content(item) for item in db.scalars(stmt).all()]


def community_content(db: Session, user: User, limit: int = 400) -> list[ContentItem]:
    """Items from other users' publicly shared collections."""
    stmt = (
        select(Item)
        .join(collection_items, collection_items.c.item_id == Item.id)
        .join(Collection, Collection.id == collection_items.c.collection_id)
        .where(Collection.share_token.is_not(None), Collection.user_id != user.id, Item.user_id != user.id)
        .options(selectinload(Item.tags))
        .distinct()
        .limit(limit)
    )
    return [item_to_content(item, origin="community") for item in db.scalars(stmt).all()]


def _online_queries(library: list[ContentItem]) -> list[tuple[str, str]]:
    """Pick (media_type, genre) pairs from the user's strongest preferences."""
    profile = build_profile(library)
    type_weight: dict[str, float] = defaultdict(float)
    genre_weight: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for item in library:
        if item.media_type not in metadata_service.SOURCE_FOR_TYPE:
            continue
        type_weight[item.media_type] += max(0.0, profile.get(f"type:{item.media_type}", 0.0))
        for genre in canonical_genres(item.genres):
            genre_weight[item.media_type][genre] += max(0.0, profile.get(f"genre:{genre}", 0.0))

    queries: list[tuple[str, str]] = []
    for media_type, _ in sorted(type_weight.items(), key=lambda pair: -pair[1])[:MAX_ONLINE_TYPES]:
        genres = sorted(genre_weight[media_type].items(), key=lambda pair: -pair[1])
        for genre, weight in genres[:GENRES_PER_TYPE]:
            if weight > 0:
                queries.append((media_type, display_genre(genre)))
    return queries


def online_content(library: list[ContentItem], media_type: str | None = None) -> tuple[list[ContentItem], list[str]]:
    candidates: list[ContentItem] = []
    errors: list[str] = []
    for query_type, genre in _online_queries(library):
        if media_type and query_type != media_type:
            continue
        try:
            results = metadata_service.discover(query_type, genre, limit=ONLINE_RESULTS_PER_QUERY)
        except CurioError as exc:
            if exc.message not in errors:
                errors.append(exc.message)
            continue
        candidates.extend(metadata_to_content(r) for r in results)
    return candidates, errors


def get_recommendations(
    db: Session,
    user: User,
    *,
    media_type: str | None = None,
    include_online: bool = False,
    limit: int = 24,
) -> RecommendationResult:
    library = library_content(db, user)
    catalogue = list(load_catalogue())
    profile = build_profile(library)

    candidates: list[ContentItem] = []
    online_errors: list[str] = []
    online_used = False
    if include_online and library:
        online, online_errors = online_content(library, media_type)
        online_used = bool(online)
        candidates.extend(online)
    candidates.extend(community_content(db, user))
    candidates.extend(catalogue)

    recommendations = recommend(library, candidates, limit=limit, media_type=media_type)
    cold_start = not recommendations and len(library) < 3
    if cold_start:
        owned = set().union(*(i.identity_keys for i in library)) if library else set()
        fresh = [c for c in catalogue if not (c.identity_keys & owned)]
        recommendations = starter_picks(fresh, limit=limit, media_type=media_type)

    return RecommendationResult(
        recommendations=recommendations,
        cold_start=cold_start,
        library_size=len(library),
        preferences=top_preferences(profile),
        online_requested=include_online,
        online_used=online_used,
        online_errors=online_errors,
    )
