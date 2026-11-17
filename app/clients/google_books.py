"""Google Books API client for book information and covers.

Docs: https://developers.google.com/books/docs/v1/using
An API key (GOOGLE_BOOKS_API_KEY) is optional; without one a small shared
quota applies.
"""

from __future__ import annotations

import re
from typing import Any

from app.clients.base import BaseClient, https, parse_year
from app.schemas.metadata import MetadataResult
from app.services.text_utils import strip_html

_VOLUME_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,40}$")


class GoogleBooksClient(BaseClient):
    source = "google_books"
    display_name = "Google Books"

    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        params = dict(extra)
        if self.settings.google_books_api_key:
            params["key"] = self.settings.google_books_api_key
        return params

    def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        params = self._params({"q": query, "maxResults": max(1, min(limit, 20)), "printType": "books"})
        data = self._get_json(self.BASE_URL, params=params, cache_key=f"gb:search:{query.lower()}:{limit}")
        results = [self._to_result(raw) for raw in data.get("items", []) or []]
        return [r for r in results if r is not None]

    def details(self, volume_id: str) -> MetadataResult:
        if not _VOLUME_ID_RE.fullmatch(volume_id):
            raise ValueError("Invalid Google Books volume id")
        data = self._get_json(f"{self.BASE_URL}/{volume_id}", params=self._params({}), cache_key=f"gb:vol:{volume_id}")
        result = self._to_result(data)
        if result is None:
            raise ValueError("Google Books returned a volume without a title")
        return result

    def discover(self, subject: str, limit: int = 10) -> list[MetadataResult]:
        """Relevant books for a subject/genre (used for online recommendations)."""
        params = self._params(
            {"q": f'subject:"{subject}"', "maxResults": max(1, min(limit, 20)), "printType": "books", "orderBy": "relevance"}
        )
        data = self._get_json(self.BASE_URL, params=params, cache_key=f"gb:subject:{subject.lower()}:{limit}")
        results = [self._to_result(raw) for raw in data.get("items", []) or []]
        return [r for r in results if r is not None]

    def _to_result(self, raw: dict[str, Any]) -> MetadataResult | None:
        info = raw.get("volumeInfo") or {}
        title = info.get("title")
        if not title or not raw.get("id"):
            return None
        images = info.get("imageLinks") or {}
        image = images.get("thumbnail") or images.get("smallThumbnail")
        if image:
            image = https(image.replace("&edge=curl", ""))
        description = strip_html(info.get("description"))[:2000] or None
        return MetadataResult(
            source="google_books",
            external_id=str(raw["id"]),
            media_type="book",
            title=str(title),
            creator=", ".join((info.get("authors") or [])[:3]) or None,
            release_year=parse_year(info.get("publishedDate")),
            description=description,
            genres=[str(c) for c in (info.get("categories") or [])],
            image_url=image,
            external_url=https(info.get("infoLink") or info.get("canonicalVolumeLink")),
        )
