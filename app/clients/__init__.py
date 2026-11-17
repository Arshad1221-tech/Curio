"""HTTP clients for external metadata providers (TMDB, Google Books, iTunes)."""

from app.clients.base import MetadataClientError, MetadataNotConfiguredError
from app.clients.google_books import GoogleBooksClient
from app.clients.itunes import ITunesClient
from app.clients.tmdb import TMDBClient

__all__ = [
    "MetadataClientError",
    "MetadataNotConfiguredError",
    "GoogleBooksClient",
    "ITunesClient",
    "TMDBClient",
]
