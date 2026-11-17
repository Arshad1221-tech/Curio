"""User account and profile schemas."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
RESERVED_USERNAMES = {"admin", "root", "curio", "api", "static", "shared", "login", "logout", "register"}


def _strip_or_none(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _check_password_strength(value: str) -> str:
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number")
    return value


def _normalise_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_PATTERN.fullmatch(value):
        raise ValueError("Enter a valid email address")
    return value


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(min_length=3, max_length=255)
    display_name: str | None = Field(default=None, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("Use 3–30 letters, numbers, dots, dashes or underscores")
        if value.lower() in RESERVED_USERNAMES:
            raise ValueError("That username is reserved; please choose another")
        return value

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return _normalise_email(value)

    @field_validator("display_name", mode="before")
    @classmethod
    def _clean_display_name(cls, value: object) -> object:
        return _strip_or_none(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return _check_password_strength(value)

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("Passwords do not match")
        return value


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    email: str = Field(min_length=3, max_length=255)
    bio: str | None = Field(default=None, max_length=500)

    @field_validator("display_name", "bio", mode="before")
    @classmethod
    def _clean_optional(cls, value: object) -> object:
        return _strip_or_none(value)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return _normalise_email(value)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return _check_password_strength(value)

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if "new_password" in info.data and value != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    display_name: str | None
    bio: str | None
    created_at: datetime
