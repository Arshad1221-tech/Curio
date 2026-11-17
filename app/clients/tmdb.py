"""TMDB (The Movie Database) client for movie and TV metadata and posters.

Docs: https://developer.themoviedb.org/reference/intro/getting-started
Requires TMDB_READ_ACCESS_TOKEN (preferred) or TMDB_API_KEY.
"""

from __future__ import annotations

from typing import Any, Literal

from app.clients.base import BaseClient, MetadataNotConfiguredError, parse_year
from app.schemas.metadata import MetadataResult
from app.services.text_utils import canonical_genres

Kind = Literal["movie", "tv"]


class TMDBClient(BaseClient):
    source = "tmdb"
    display_name = "TMDB"

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
    WEB_BASE = "https://www.themoviedb.org"

    @property
    def enabled(self) -> bool:
        return self.settings.tmdb_enabled

    # --- Low-level request -------------------------------------------------------
    def _request(self, path: str, params: dict[str, Any] | None = None, cache: bool = True) -> dict[str, Any]:
        if not self.enabled:
            raise MetadataNotConfiguredError(
                "Movie and TV lookup needs a TMDB API key. Add TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY to your .env file."
            )
        query: dict[str, Any] = {"language": "en-US", **(params or {})}
        headers: dict[str, str] = {}
        if self.settings.tmdb_read_access_token:
            headers["Authorization"] = f"Bearer {self.settings.tmdb_read_access_token}"
        else:
            query["api_key"] = self.settings.tmdb_api_key
        cache_key = None
        if cache:
            # The key never contains credentials.
            cache_key = "tmdb:" + path + "?" + "&".join(f"{k}={v}" for k, v in sorted(query.items()) if k != "api_key")
        return self._get_json(f"{self.BASE_URL}{path}", params=query, headers=headers, cache_key=cache_key)

    # --- Public API -------------------------------------------------------------
    def genre_map(self, kind: Kind) -> dict[int, str]:
        data = self._request(f"/genre/{kind}/list")
        return {int(g["id"]): str(g["name"]) for g in data.get("genres", []) if "id" in g and "name" in g}

    def search(self, query: str, kind: Kind, limit: int = 10) -> list[MetadataResult]:
        data = self._request(f"/search/{kind}", {"query": query, "include_adult": "false", "page": 1})
        genres = self._safe_genre_map(kind)
        results = [self._to_result(raw, kind, genres) for raw in data.get("results", [])]
        return [r for r in results if r is not None][:limit]

    def details(self, kind: Kind, external_id: str) -> MetadataResult:
        if not external_id.isdigit():
            raise ValueError("TMDB ids are numeric")
        data = self._request(f"/{kind}/{external_id}", {"append_to_response": "credits,keywords"})
        result = self._to_result(data, kind, {})
        if result is None:
            raise ValueError("TMDB returned an item without a title")

        result.genres = [g["name"] for g in data.get("genres", []) if g.get("name")]
        if kind == "movie":
            crew = (data.get("credits") or {}).get("crew", [])
            directors = [p["name"] for p in crew if p.get("job") == "Director" and p.get("name")]
            result.creator = ", ".join(dict.fromkeys(directors)) or None
            keyword_items = (data.get("keywords") or {}).get("keywords", [])
        else:
            creators = [p["name"] for p in data.get("created_by", []) if p.get("name")]
            networks = [n["name"] for n in data.get("networks", []) if n.get("name")]
            result.creator = ", ".join(creators) or (networks[0] if networks else None)
            keyword_items = (data.get("keywords") or {}).get("results", [])
        result.keywords = [k["name"].lower() for k in keyword_items if k.get("name")][:15]
        return result

    def discover(self, kind: Kind, genre: str, limit: int = 10) -> list[MetadataResult]:
        """Popular titles for a genre name (used for online recommendations)."""
        genres = self._safe_genre_map(kind)
        target = canonical_genres(genre)
        if not target:
            return []
        genre_id = next((gid for gid, name in genres.items() if target[0] in canonical_genres(name)), None)
        if genre_id is None:
            return []
        data = self._request(
            f"/discover/{kind}",
            {"with_genres": genre_id, "sort_by": "popularity.desc", "vote_count.gte": 200, "include_adult": "false"},
        )
        results = [self._to_result(raw, kind, genres) for raw in data.get("results", [])]
        return [r for r in results if r is not None][:limit]

    # --- Helpers ----------------------------------------------------------------
    def _safe_genre_map(self, kind: Kind) -> dict[int, str]:
        try:
            return self.genre_map(kind)
        except Exception:  # genre names are a nice-to-have for search results
            return {}

    def _to_result(self, raw: dict[str, Any], kind: Kind, genre_names: dict[int, str]) -> MetadataResult | None:
        title = raw.get("title") or raw.get("name")
        if not title or raw.get("id") is None:
            return None
        poster = raw.get("poster_path")
        return MetadataResult(
            source="tmdb",
            external_id=str(raw["id"]),
            media_type="movie" if kind == "movie" else "tv",
            title=str(title),
            release_year=parse_year(raw.get("release_date") or raw.get("first_air_date")),
            description=(raw.get("overview") or None),
            genres=[genre_names[g] for g in raw.get("genre_ids", []) if g in genre_names],
            image_url=f"{self.IMAGE_BASE}{poster}" if poster else None,
            external_url=f"{self.WEB_BASE}/{kind}/{raw['id']}",
        )
