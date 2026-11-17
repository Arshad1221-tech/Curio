"""Text normalisation helpers shared by item management and recommendations."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

_WHITESPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-z][a-z'\-]{2,}")
_HTML_TAG_RE = re.compile(r"<[^>]+>")

STOPWORDS = frozenset(
    """
    a about above after again against all almost also although always am among an and another any anyone
    anything are around as at away back be became because become becomes been before being below best
    between both but by came can cannot could did do does doing done down during each either else even
    ever every few find finds first for found from further get gets give given gives go goes going got
    had has have having he her here hers herself him himself his how however i if in into is it its
    itself just know known last later least less like made make makes making many may me might more
    most much must my myself near need never new next no nor not now of off often on once one only
    onto or other others our ours ourselves out over own part people put rather really same see seems
    set several she should show shows since so some something soon still such take takes taking than
    that the their theirs them themselves then there these they thing things this those though three
    through thus to together too two under until up upon us use used very via was way ways we well
    were what whatever when where whether which while who whole whom whose why will with within without
    would year years yet you your yours yourself yourselves
    book books novel novels story stories film films movie movies series season seasons episode episodes
    song songs album albums track tracks edition volume author written writer director directed star
    stars starring life lives world time times day days man men woman women young old bestselling
    acclaimed award winning bestseller classic must-read
    travels travel mysterious dangerous secret secrets control against forms beloved famous opening title
    begins begin follows follow tells tell including whose era home
    """.split()
)

# Canonical genre names (lower-case) so "Sci-Fi" and "Science Fiction" match.
GENRE_SYNONYMS: dict[str, str] = {
    "sci-fi": "science fiction",
    "scifi": "science fiction",
    "sci fi": "science fiction",
    "science-fiction": "science fiction",
    "sf": "science fiction",
    "hip hop": "hip-hop",
    "hiphop": "hip-hop",
    "rap/hip-hop": "hip-hop",
    "rnb": "r&b",
    "r & b": "r&b",
    "rhythm and blues": "r&b",
    "self help": "self-help",
    "nonfiction": "non-fiction",
    "non fiction": "non-fiction",
    "thrillers": "thriller",
    "mysteries": "mystery",
    "comedies": "comedy",
    "musicals": "musical",
    "documentaries": "documentary",
    "young adult fiction": "young adult",
    "juvenile fiction": "young adult",
    "biography & autobiography": "biography",
    "kids": "family",
    "suspense": "thriller",
    "electronica": "electronic",
    "dance-pop": "pop",
}
DROPPED_GENRES = frozenset({"general", "other", "misc", "miscellaneous", "music"})
GENRE_DISPLAY_OVERRIDES: dict[str, str] = {"r&b": "R&B", "tv movie": "TV Movie", "edm": "EDM", "k-pop": "K-Pop"}


def normalise_label(value: str) -> str:
    """Lower-case, trim and collapse internal whitespace."""
    return _WHITESPACE_RE.sub(" ", value).strip().lower()


def strip_html(value: str | None) -> str:
    return _HTML_TAG_RE.sub(" ", value or "").strip()


def _iter_values(values: Iterable[str] | str | None) -> Iterable[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return values.split(",")
    result: list[str] = []
    for value in values:
        if isinstance(value, str):
            result.extend(value.split(","))
    return result


def clean_list(
    values: Iterable[str] | str | None,
    *,
    max_items: int,
    max_length: int = 40,
    lower: bool = False,
) -> list[str]:
    """Split on commas, trim, truncate and de-duplicate (case-insensitively)."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in _iter_values(values):
        value = _WHITESPACE_RE.sub(" ", raw).strip().lstrip("#").strip()
        if not value:
            continue
        value = value[:max_length].strip()
        if lower:
            value = value.lower()
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
        if len(cleaned) >= max_items:
            break
    return cleaned


def to_csv(values: Iterable[str]) -> str:
    return ",".join(v.replace(",", " ").strip() for v in values if v and v.strip())


def canonical_genres(values: Iterable[str] | str | None) -> list[str]:
    """Return lower-case canonical genres, splitting compound labels.

    ``"Sci-Fi & Fantasy"`` -> ``["science fiction", "fantasy"]``
    ``"Fiction / Science Fiction / General"`` -> ``["fiction", "science fiction"]``
    """
    result: list[str] = []
    for raw in _iter_values(values):
        label = normalise_label(raw)
        if not label:
            continue
        parts = [GENRE_SYNONYMS[label]] if label in GENRE_SYNONYMS else re.split(r"\s*/\s*|\s+&\s+", label)
        for part in parts:
            part = normalise_label(part)
            part = GENRE_SYNONYMS.get(part, part)
            if part and part not in DROPPED_GENRES and part not in result:
                result.append(part)
    return result


def display_genre(genre: str) -> str:
    """Human-friendly capitalisation for a canonical genre."""
    key = normalise_label(genre)
    if key in GENRE_DISPLAY_OVERRIDES:
        return GENRE_DISPLAY_OVERRIDES[key]
    words = []
    for word in key.split(" "):
        words.append("-".join(piece[:1].upper() + piece[1:] for piece in word.split("-")))
    return " ".join(words)


def extract_keywords(*texts: str | None, limit: int = 12) -> list[str]:
    """Very small keyword extractor: frequent non-stopword terms, in order of importance."""
    counts: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    position = 0
    for text in texts:
        for match in _WORD_RE.finditer(strip_html(text).lower()):
            word = match.group(0).strip("'-")
            if word.endswith("'s"):
                word = word[:-2]
            if len(word) < 3 or word in STOPWORDS:
                continue
            counts[word] += 1
            first_seen.setdefault(word, position)
            position += 1
    ranked = sorted(counts, key=lambda w: (-counts[w], first_seen[w]))
    return ranked[:limit]


def merge_unique(*lists: Iterable[str], limit: int) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for values in lists:
        for value in values:
            key = value.lower()
            if key and key not in seen:
                seen.add(key)
                merged.append(value)
                if len(merged) >= limit:
                    return merged
    return merged
