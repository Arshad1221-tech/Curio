"""Normalised metadata returned by the external API clients."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MetadataSource = Literal["tmdb", "google_books", "itunes"]


class MetadataResult(BaseModel):
    """One search result from TMDB, Google Books or iTunes in a common shape."""

    source: MetadataSource
    external_id: str
    media_type: str
    title: str
    creator: str | None = None
    release_year: int | None = None
    description: str | None = None
    genres: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    image_url: str | None = None
    external_url: str | None = None


class MetadataSearchResponse(BaseModel):
    source: MetadataSource
    query: str
    results: list[MetadataResult]


class MetadataSourceStatus(BaseModel):
    key: MetadataSource
    name: str
    media_types: list[str]
    enabled: bool
    requires_key: bool
    note: str
