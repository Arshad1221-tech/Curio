"""Content-based recommendation engine (pure Python, no paid AI services).

How it works
------------
1. **Feature extraction** - every item becomes a sparse vector of weighted
   features: ``genre:*``, ``tag:*``, ``creator:*``, ``keyword:*`` and
   ``type:*``. Genres are normalised so "Sci-Fi" and "Science Fiction" match.
2. **User profile** - the vectors of the items in the user's library are summed,
   each multiplied by a *preference weight* derived from the user's rating and
   favourite flag. Low ratings (1-2 stars) give negative weights, so disliked
   traits push candidates down.
3. **IDF weighting** - features that appear on almost every item (e.g. "Drama")
   carry less information than rare ones, so each feature is scaled by its
   inverse document frequency across the library and the candidate pool.
4. **Scoring** - each candidate the user doesn't already own is scored with
   cosine similarity between the profile and the candidate vector. Candidates
   that only match on media type are ignored.
5. **Explanations** - the features that contributed most to the score are
   turned into human-readable reasons ("You enjoy Science Fiction").

The module has no database dependencies so it can be unit-tested in isolation.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from app.services.text_utils import canonical_genres, display_genre, normalise_label

FEATURE_WEIGHTS: dict[str, float] = {
    "genre": 1.0,
    "tag": 0.8,
    "creator": 0.7,
    "keyword": 0.45,
    "type": 0.25,
}
MAX_KEYWORDS_PER_ITEM = 15
FAVOURITE_BONUS = 1.5


@dataclass
class ContentItem:
    """Engine-level representation of a library item or candidate."""

    media_type: str
    title: str
    creator: str | None = None
    release_year: int | None = None
    description: str | None = None
    genres: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    image_url: str | None = None
    source: str = "catalogue"  # metadata source used for identity (tmdb, itunes, catalogue...)
    external_id: str | None = None
    external_url: str | None = None
    origin: str = "catalogue"  # where the candidate came from: catalogue, community or online
    rating: int | None = None
    is_favourite: bool = False
    starter: bool = False

    @property
    def identity_keys(self) -> set[str]:
        """Keys used to detect that two records describe the same work."""
        keys = {f"{self.media_type}:title:{normalise_label(self.title)}"}
        if self.external_id:
            keys.add(f"{self.media_type}:{self.source}:{self.external_id}")
        return keys


@dataclass
class Recommendation:
    item: ContentItem
    score: float
    reasons: list[str]
    match_percent: int = 0


def _creator_names(creator: str | None) -> list[str]:
    if not creator:
        return []
    return [normalise_label(name) for name in creator.replace("&", ",").split(",") if name.strip()]


def feature_vector(item: ContentItem) -> dict[str, float]:
    """Sparse weighted feature vector for one item."""
    vector: dict[str, float] = {}
    for genre in canonical_genres(item.genres):
        vector[f"genre:{genre}"] = FEATURE_WEIGHTS["genre"]
    for tag in item.tags:
        if tag.strip():
            vector[f"tag:{normalise_label(tag)}"] = FEATURE_WEIGHTS["tag"]
    for name in _creator_names(item.creator):
        vector[f"creator:{name}"] = FEATURE_WEIGHTS["creator"]
    for keyword in item.keywords[:MAX_KEYWORDS_PER_ITEM]:
        if keyword.strip():
            vector.setdefault(f"keyword:{normalise_label(keyword)}", FEATURE_WEIGHTS["keyword"])
    vector[f"type:{item.media_type}"] = FEATURE_WEIGHTS["type"]
    return vector


def preference_weight(rating: int | None, is_favourite: bool) -> float:
    """How strongly an item should shape the profile.

    Unrated: 1.0 | 1★: -1.2 | 2★: -0.4 | 3★: 0.4 | 4★: 1.2 | 5★: 2.0, plus 1.5 for favourites.
    """
    weight = 1.0 if rating is None else (rating - 2.5) * 0.8
    if is_favourite:
        weight += FAVOURITE_BONUS
    return weight


def build_profile(library: Iterable[ContentItem]) -> dict[str, float]:
    profile: dict[str, float] = defaultdict(float)
    for item in library:
        weight = preference_weight(item.rating, item.is_favourite)
        for feature, value in feature_vector(item).items():
            profile[feature] += weight * value
    return dict(profile)


def inverse_document_frequency(vectors: Sequence[dict[str, float]]) -> dict[str, float]:
    total = len(vectors)
    document_frequency: Counter[str] = Counter()
    for vector in vectors:
        document_frequency.update(vector.keys())
    return {feature: math.log((1 + total) / (1 + count)) + 1.0 for feature, count in document_frequency.items()}


def cosine_similarity(
    profile: dict[str, float], vector: dict[str, float], idf: dict[str, float]
) -> tuple[float, dict[str, float]]:
    """Cosine similarity with IDF weighting; also returns per-feature contributions."""
    contributions: dict[str, float] = {}
    dot = 0.0
    for feature, candidate_value in vector.items():
        profile_value = profile.get(feature)
        if not profile_value:
            continue
        weight = idf.get(feature, 1.0)
        contribution = (profile_value * weight) * (candidate_value * weight)
        contributions[feature] = contribution
        dot += contribution
    profile_norm = math.sqrt(sum((v * idf.get(f, 1.0)) ** 2 for f, v in profile.items()))
    vector_norm = math.sqrt(sum((v * idf.get(f, 1.0)) ** 2 for f, v in vector.items()))
    if profile_norm == 0 or vector_norm == 0:
        return 0.0, {}
    return dot / (profile_norm * vector_norm), contributions


def _quote_list(values: list[str]) -> str:
    quoted = [f"“{v}”" for v in values]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " and " + quoted[-1]


def _join(values: list[str]) -> str:
    return values[0] if len(values) == 1 else ", ".join(values[:-1]) + " and " + values[-1]


def explain(item: ContentItem, contributions: dict[str, float], max_reasons: int = 3) -> list[str]:
    """Turn the strongest positive feature contributions into readable reasons."""
    grouped: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for feature, value in contributions.items():
        if value <= 0:
            continue
        kind, _, name = feature.partition(":")
        if kind != "type":
            grouped[kind].append((value, name))

    order = sorted(grouped, key=lambda kind: -max(v for v, _ in grouped[kind]))
    original_creators = {normalise_label(n): n.strip() for n in (item.creator or "").replace("&", ",").split(",")}
    reasons: list[str] = []
    for kind in order:
        names = [name for _, name in sorted(grouped[kind], reverse=True)][:2]
        if kind == "genre":
            reasons.append(f"Matches your taste for {_join([display_genre(n) for n in names])}")
        elif kind == "creator":
            reasons.append(f"More from {_join([original_creators.get(n, n.title()) for n in names])}")
        elif kind == "tag":
            reasons.append(f"Similar to things you tagged {_quote_list(names)}")
        elif kind == "keyword":
            reasons.append(f"Shares themes like {_quote_list(names)}")
        if len(reasons) >= max_reasons:
            break
    return reasons


def has_positive_preferences(profile: dict[str, float]) -> bool:
    return any(value > 0 for feature, value in profile.items() if not feature.startswith("type:"))


def recommend(
    library: Sequence[ContentItem],
    candidates: Iterable[ContentItem],
    *,
    limit: int = 12,
    media_type: str | None = None,
) -> list[Recommendation]:
    """Rank ``candidates`` for a user whose saved items are ``library``."""
    profile = build_profile(library)
    if not has_positive_preferences(profile):
        return []

    owned: set[str] = set()
    for item in library:
        owned |= item.identity_keys

    pool: list[ContentItem] = []
    seen: set[str] = set()
    for candidate in candidates:
        if media_type and candidate.media_type != media_type:
            continue
        keys = candidate.identity_keys
        if keys & owned or keys & seen:
            continue
        seen |= keys
        pool.append(candidate)

    vectors = [feature_vector(c) for c in pool]
    idf = inverse_document_frequency(vectors + [feature_vector(i) for i in library])

    recommendations: list[Recommendation] = []
    for candidate, vector in zip(pool, vectors):
        score, contributions = cosine_similarity(profile, vector, idf)
        meaningful = {f: v for f, v in contributions.items() if v > 0 and not f.startswith("type:")}
        if score <= 0 or not meaningful:
            continue
        recommendations.append(Recommendation(item=candidate, score=score, reasons=explain(candidate, meaningful)))

    recommendations.sort(key=lambda r: (-r.score, r.item.title.lower()))
    top = recommendations[:limit]

    # Present scores relative to the best match so the strongest suggestion reads ~95%.
    best = top[0].score if top else 0.0
    for rec in top:
        rec.match_percent = max(1, min(99, round(95 * rec.score / best))) if best else 0
    return top


def starter_picks(candidates: Iterable[ContentItem], *, limit: int = 12, media_type: str | None = None) -> list[Recommendation]:
    """Cold-start suggestions when the user has not saved enough to build a profile."""
    picks = [c for c in candidates if c.starter and (not media_type or c.media_type == media_type)]
    return [
        Recommendation(item=c, score=0.0, reasons=["A well-loved pick to start your collection"])
        for c in picks[:limit]
    ]


def top_preferences(profile: dict[str, float], limit: int = 8) -> list[tuple[str, str]]:
    """Strongest positive genre/creator/tag features as ``(kind, display_name)`` pairs."""
    ranked = sorted(
        ((value, feature) for feature, value in profile.items() if value > 0 and feature.split(":", 1)[0] in {"genre", "creator", "tag"}),
        reverse=True,
    )
    result: list[tuple[str, str]] = []
    for _, feature in ranked[:limit]:
        kind, _, name = feature.partition(":")
        label = display_genre(name) if kind == "genre" else (f"#{name}" if kind == "tag" else name.title())
        result.append((kind, label))
    return result
