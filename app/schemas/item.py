"""Item input/output schemas."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import DEFAULT_STATUS, MAX_GENRES_PER_ITEM, MAX_KEYWORDS_PER_ITEM, MAX_TAGS_PER_ITEM
from app.services.text_utils import canonical_genres, clean_list, display_genre

MediaType = Literal["book", "movie", "tv", "song", "album", "other"]
Status = Literal["wishlist", "in_progress", "completed"]
ExternalSource = Literal["manual", "tmdb", "google_books", "itunes", "catalogue", "community"]

_URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
_TRUTHY = {"1", "true", "on", "yes"}


def _strip_or_none(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class ItemIn(BaseModel):
    """Validated data for creating or updating an item (from forms or JSON)."""

    media_type: MediaType
    title: str = Field(min_length=1, max_length=255)
    creator: str | None = Field(default=None, max_length=255)
    release_year: int | None = Field(default=None, ge=1000, le=2100)
    description: str | None = Field(default=None, max_length=5000)
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    image_url: str | None = Field(default=None, max_length=1000)
    external_source: ExternalSource = "manual"
    external_id: str | None = Field(default=None, max_length=100)
    external_url: str | None = Field(default=None, max_length=1000)
    rating: int | None = Field(default=None, ge=1, le=5)
    is_favourite: bool = False
    status: Status = DEFAULT_STATUS  # type: ignore[assignment]
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("media_type", mode="before")
    @classmethod
    def _media_type(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().lower()
            if not value:
                raise ValueError("Choose what kind of item this is")
        return value

    @field_validator("title", mode="before")
    @classmethod
    def _title(cls, value: object) -> object:
        if isinstance(value, str):
            value = " ".join(value.split())
            if not value:
                raise ValueError("Title is required")
        return value

    @field_validator("creator", "description", "notes", "image_url", "external_id", "external_url", mode="before")
    @classmethod
    def _optional_text(cls, value: object) -> object:
        return _strip_or_none(value)

    @field_validator("release_year", "rating", mode="before")
    @classmethod
    def _optional_int(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value or value == "0":
                return None
        return value

    @field_validator("external_source", mode="before")
    @classmethod
    def _source(cls, value: object) -> object:
        return value.strip() or "manual" if isinstance(value, str) else (value or "manual")

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: object) -> object:
        return value.strip() or DEFAULT_STATUS if isinstance(value, str) else (value or DEFAULT_STATUS)

    @field_validator("is_favourite", mode="before")
    @classmethod
    def _favourite(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower() in _TRUTHY
        return bool(value)

    @field_validator("genres", mode="before")
    @classmethod
    def _genres(cls, value: object) -> list[str]:
        genres = canonical_genres(value if isinstance(value, (str, list, tuple)) else None)
        return [display_genre(g) for g in genres[:MAX_GENRES_PER_ITEM]]

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, value: object) -> list[str]:
        return clean_list(value if isinstance(value, (str, list, tuple)) else None, max_items=MAX_TAGS_PER_ITEM, lower=True)

    @field_validator("keywords", mode="before")
    @classmethod
    def _keywords(cls, value: object) -> list[str]:
        return clean_list(
            value if isinstance(value, (str, list, tuple)) else None,
            max_items=MAX_KEYWORDS_PER_ITEM,
            max_length=40,
            lower=True,
        )

    @field_validator("image_url", "external_url")
    @classmethod
    def _url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _URL_RE.match(value):
            raise ValueError("Enter a full web address starting with http:// or https://")
        if value.lower().startswith("http://"):
            value = "https://" + value[7:]  # avoid mixed-content warnings for cover images
        return value


class ItemOut(BaseModel):
    """JSON representation of an item."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    media_type: str
    title: str
    creator: str | None
    release_year: int | None
    description: str | None
    genres: list[str] = Field(validation_alias="genre_list")
    tags: list[str] = Field(validation_alias="tag_names")
    image_url: str | None
    rating: int | None
    is_favourite: bool
    status: str
    notes: str | None
    external_source: str
    external_id: str | None
    created_at: datetime
    updated_at: datetime


class FavouriteOut(BaseModel):
    id: int
    is_favourite: bool
