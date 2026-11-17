"""Domain constants shared by models, schemas, services and templates."""

from __future__ import annotations

MEDIA_TYPES: dict[str, dict[str, str]] = {
    "book": {"label": "Book", "plural": "Books", "icon": "bi-book", "creator": "Author"},
    "movie": {"label": "Movie", "plural": "Movies", "icon": "bi-film", "creator": "Director"},
    "tv": {"label": "TV Show", "plural": "TV Shows", "icon": "bi-tv", "creator": "Creator"},
    "song": {"label": "Song", "plural": "Songs", "icon": "bi-music-note-beamed", "creator": "Artist"},
    "album": {"label": "Album", "plural": "Albums", "icon": "bi-vinyl", "creator": "Artist"},
    "other": {"label": "Other", "plural": "Other interests", "icon": "bi-stars", "creator": "Creator"},
}

MEDIA_TYPE_KEYS: tuple[str, ...] = tuple(MEDIA_TYPES.keys())

# Square artwork (music) vs. portrait posters/covers (everything else).
SQUARE_ARTWORK_TYPES = frozenset({"song", "album"})

STATUSES: dict[str, str] = {
    "wishlist": "Wishlist",
    "in_progress": "In progress",
    "completed": "Completed",
}
STATUS_KEYS: tuple[str, ...] = tuple(STATUSES.keys())
DEFAULT_STATUS = "completed"

EXTERNAL_SOURCES: dict[str, str] = {
    "manual": "Added manually",
    "tmdb": "TMDB",
    "google_books": "Google Books",
    "itunes": "iTunes",
    "catalogue": "Curio catalogue",
    "community": "Curio community",
}

SORT_OPTIONS: dict[str, str] = {
    "recent": "Recently added",
    "title": "Title (A–Z)",
    "rating": "Highest rated",
    "year": "Newest release",
}

ITEMS_PER_PAGE = 24
MAX_TAGS_PER_ITEM = 20
MAX_GENRES_PER_ITEM = 12
MAX_KEYWORDS_PER_ITEM = 20
