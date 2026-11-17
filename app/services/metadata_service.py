"""Facade over the external metadata clients.

Chooses the right provider for each media type and converts client errors
into user-facing domain errors.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.clients import GoogleBooksClient, ITunesClient, MetadataClientError, MetadataNotConfiguredError, TMDBClient
from app.config import get_settings
from app.core.errors import CurioError, ExternalServiceError, ServiceNotConfiguredError
from app.schemas.metadata import MetadataResult, MetadataSourceStatus

SOURCE_FOR_TYPE: dict[str, str] = {
    "book": "google_books",
    "movie": "tmdb",
    "tv": "tmdb",
    "song": "itunes",
    "album": "itunes",
}
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@lru_cache(maxsize=1)
def tmdb_client() -> TMDBClient:
    return TMDBClient(get_settings())


@lru_cache(maxsize=1)
def google_books_client() -> GoogleBooksClient:
    return GoogleBooksClient(get_settings())


@lru_cache(maxsize=1)
def itunes_client() -> ITunesClient:
    return ITunesClient(get_settings())


def source_statuses() -> list[MetadataSourceStatus]:
    settings = get_settings()
    return [
        MetadataSourceStatus(
            key="tmdb", name="TMDB", media_types=["movie", "tv"], enabled=settings.tmdb_enabled, requires_key=True,
            note="Configured" if settings.tmdb_enabled else "Add TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY to .env",
        ),
        MetadataSourceStatus(
            key="google_books", name="Google Books", media_types=["book"], enabled=True, requires_key=False,
            note="Using your API key" if settings.google_books_api_key else "Works without a key (shared quota)",
        ),
        MetadataSourceStatus(
            key="itunes", name="iTunes Search", media_types=["song", "album"], enabled=True, requires_key=False,
            note="No key required",
        ),
    ]


def lookup_availability() -> dict[str, bool]:
    """Which media types can currently be looked up online."""
    enabled = {status.key: status.enabled for status in source_statuses()}
    return {media_type: enabled[source] for media_type, source in SOURCE_FOR_TYPE.items()}


def _wrap(exc: MetadataClientError) -> CurioError:
    if isinstance(exc, MetadataNotConfiguredError):
        return ServiceNotConfiguredError(str(exc))
    return ExternalServiceError(str(exc))


def search(media_type: str, query: str, limit: int = 10) -> list[MetadataResult]:
    query = " ".join(query.split())[:120]
    if len(query) < 2:
        raise CurioError("Type at least two characters to search.")
    try:
        if media_type == "book":
            return google_books_client().search(query, limit=limit)
        if media_type in ("movie", "tv"):
            return tmdb_client().search(query, kind=media_type, limit=limit)  # type: ignore[arg-type]
        if media_type in ("song", "album"):
            return itunes_client().search(query, entity=media_type, limit=limit)  # type: ignore[arg-type]
    except MetadataClientError as exc:
        raise _wrap(exc) from exc
    raise CurioError("Online lookup isn't available for this type — please enter the details yourself.")


def details(media_type: str, source: str, external_id: str) -> MetadataResult:
    if not _SAFE_ID_RE.fullmatch(external_id or ""):
        raise CurioError("Invalid item identifier.")
    if SOURCE_FOR_TYPE.get(media_type) != source:
        raise CurioError("That source doesn't provide this type of item.")
    try:
        if source == "google_books":
            return google_books_client().details(external_id)
        if source == "tmdb":
            return tmdb_client().details(media_type, external_id)  # type: ignore[arg-type]
        if source == "itunes":
            return itunes_client().details(external_id, entity=media_type)  # type: ignore[arg-type]
    except MetadataClientError as exc:
        raise _wrap(exc) from exc
    except ValueError as exc:
        raise CurioError(str(exc)) from exc
    raise CurioError("Unknown metadata source.")


def discover(media_type: str, genre: str, limit: int = 10) -> list[MetadataResult]:
    """Genre-based candidates from the online catalogue (raises ``CurioError`` on failure)."""
    try:
        if media_type == "book":
            return google_books_client().discover(genre, limit=limit)
        if media_type in ("movie", "tv"):
            client = tmdb_client()
            return client.discover(media_type, genre, limit=limit) if client.enabled else []  # type: ignore[arg-type]
        if media_type in ("song", "album"):
            return itunes_client().discover(genre, entity=media_type, limit=limit)  # type: ignore[arg-type]
    except MetadataClientError as exc:
        raise _wrap(exc) from exc
    return []
