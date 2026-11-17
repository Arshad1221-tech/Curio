"""iTunes Search API client for songs, albums and artwork.

Docs: https://performance-partners.apple.com/search-api
No API key is required. Apple asks clients to stay at roughly 20 calls/minute.
"""

from __future__ import annotations

from typing import Any, Literal

from app.clients.base import BaseClient, https, parse_year
from app.schemas.metadata import MetadataResult

Entity = Literal["song", "album"]


class ITunesClient(BaseClient):
    source = "itunes"
    display_name = "iTunes"

    SEARCH_URL = "https://itunes.apple.com/search"
    LOOKUP_URL = "https://itunes.apple.com/lookup"

    def search(self, query: str, entity: Entity = "song", limit: int = 10) -> list[MetadataResult]:
        params = {
            "term": query,
            "media": "music",
            "entity": entity,
            "limit": max(1, min(limit, 25)),
            "country": self.settings.itunes_country,
        }
        data = self._get_json(self.SEARCH_URL, params=params, cache_key=f"it:{entity}:{query.lower()}:{limit}")
        results = [self._to_result(raw, entity) for raw in data.get("results", [])]
        return [r for r in results if r is not None]

    def details(self, external_id: str, entity: Entity = "song") -> MetadataResult:
        if not external_id.isdigit():
            raise ValueError("iTunes ids are numeric")
        params = {"id": external_id, "country": self.settings.itunes_country}
        data = self._get_json(self.LOOKUP_URL, params=params, cache_key=f"it:lookup:{external_id}")
        for raw in data.get("results", []):
            result = self._to_result(raw, entity)
            if result is not None:
                return result
        raise ValueError("iTunes did not return that item")

    def discover(self, genre: str, entity: Entity = "song", limit: int = 10) -> list[MetadataResult]:
        """Search by genre term (the public API has no 'popular by genre' endpoint)."""
        return self.search(genre, entity=entity, limit=limit)

    def _to_result(self, raw: dict[str, Any], entity: Entity) -> MetadataResult | None:
        artwork = raw.get("artworkUrl100") or raw.get("artworkUrl60")
        if artwork:
            artwork = https(artwork.replace("100x100bb", "600x600bb").replace("60x60bb", "600x600bb"))
        genre = raw.get("primaryGenreName")

        if entity == "album" or raw.get("wrapperType") == "collection":
            title = raw.get("collectionName")
            identifier = raw.get("collectionId")
            if not title or identifier is None:
                return None
            tracks = raw.get("trackCount")
            description = f"Album with {tracks} tracks." if tracks else None
            return MetadataResult(
                source="itunes",
                external_id=str(identifier),
                media_type="album",
                title=str(title),
                creator=raw.get("artistName"),
                release_year=parse_year(raw.get("releaseDate")),
                description=description,
                genres=[genre] if genre else [],
                image_url=artwork,
                external_url=https(raw.get("collectionViewUrl")),
            )

        title = raw.get("trackName")
        identifier = raw.get("trackId")
        if not title or identifier is None:
            return None
        album = raw.get("collectionName")
        return MetadataResult(
            source="itunes",
            external_id=str(identifier),
            media_type="song",
            title=str(title),
            creator=raw.get("artistName"),
            release_year=parse_year(raw.get("releaseDate")),
            description=f"From the album “{album}”." if album else None,
            genres=[genre] if genre else [],
            image_url=artwork,
            external_url=https(raw.get("trackViewUrl")),
        )
