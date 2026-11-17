"""Shared HTTP plumbing for metadata clients: timeouts, error mapping and caching."""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, ClassVar

import httpx

from app.config import Settings

logger = logging.getLogger("curio.clients")

USER_AGENT = "Curio/1.0 (personal collections web app)"
_YEAR_RE = re.compile(r"(\d{4})")


class MetadataClientError(Exception):
    """An external API could not be reached or returned an error."""


class MetadataNotConfiguredError(MetadataClientError):
    """The API needs credentials that are not configured."""


def parse_year(value: str | None) -> int | None:
    if not value:
        return None
    match = _YEAR_RE.search(value)
    if not match:
        return None
    year = int(match.group(1))
    return year if 1000 <= year <= 2100 else None


def https(url: str | None) -> str | None:
    if not url:
        return None
    return "https://" + url[7:] if url.startswith("http://") else url


class TTLCache:
    """Tiny thread-safe in-memory cache with per-entry expiry."""

    def __init__(self, ttl_seconds: int = 1800, max_entries: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.monotonic():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self.max_entries:
                oldest = min(self._data, key=lambda k: self._data[k][0])
                self._data.pop(oldest, None)
            self._data[key] = (time.monotonic() + self.ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class BaseClient:
    """Base class providing a JSON GET helper with consistent error handling."""

    source: ClassVar[str] = ""
    display_name: ClassVar[str] = ""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self._transport = transport  # injectable for tests
        self._cache = TTLCache()

    @property
    def enabled(self) -> bool:
        return True

    def _get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cache_key: str | None = None,
    ) -> Any:
        if cache_key:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        request_headers.update(headers or {})
        try:
            with httpx.Client(timeout=self.settings.http_timeout, transport=self._transport) as client:
                response = client.get(url, params=params, headers=request_headers)
        except httpx.TimeoutException as exc:
            raise MetadataClientError(f"{self.display_name} took too long to respond. Please try again.") from exc
        except httpx.HTTPError as exc:
            logger.warning("%s request failed: %s", self.display_name, exc)
            raise MetadataClientError(f"Couldn't reach {self.display_name}. Check your internet connection.") from exc

        if response.status_code in (401, 403):
            raise MetadataNotConfiguredError(
                f"{self.display_name} rejected the API credentials. Check the keys in your .env file."
            )
        if response.status_code == 404:
            raise MetadataClientError(f"{self.display_name} couldn't find that title.")
        if response.status_code == 429:
            raise MetadataClientError(f"{self.display_name} rate limit reached. Please wait a moment and try again.")
        if response.status_code >= 400:
            logger.warning("%s returned HTTP %s", self.display_name, response.status_code)
            raise MetadataClientError(f"{self.display_name} returned an error (HTTP {response.status_code}).")

        try:
            data = response.json()
        except ValueError as exc:
            raise MetadataClientError(f"{self.display_name} returned an unexpected response.") from exc

        if cache_key:
            self._cache.set(cache_key, data)
        return data
