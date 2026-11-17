"""Collection input/output schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, value: object) -> object:
        if isinstance(value, str):
            value = " ".join(value.split())
            if not value:
                raise ValueError("Give your collection a name")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def _description(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    item_count: int
    is_shared: bool
    created_at: datetime
    updated_at: datetime
