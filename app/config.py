"""Application configuration.

All settings are read from environment variables (optionally loaded from a
local ``.env`` file). Secrets such as API keys are never hard-coded.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

APP_NAME = "Curio"
TAGLINE = "Collect what you love. Discover what’s next."

load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("curio")

_PLACEHOLDER_SECRETS = {"", "change-me", "changeme", "secret"}


def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        logger.warning("Invalid integer for %s; using default %s", name, default)
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except ValueError:
        logger.warning("Invalid number for %s; using default %s", name, default)
        return default


def _default_database_url() -> str:
    return f"sqlite:///{(DATA_DIR / 'curio.db').as_posix()}"


@dataclass(frozen=True)
class Settings:
    """Typed, immutable view of the runtime configuration."""

    environment: str
    debug: bool
    secret_key: str
    secret_key_is_temporary: bool
    database_url: str
    session_max_age: int
    secure_cookies: bool
    http_timeout: float
    tmdb_api_key: str
    tmdb_read_access_token: str
    google_books_api_key: str
    itunes_country: str
    app_name: str = APP_NAME
    tagline: str = TAGLINE

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key or self.tmdb_read_access_token)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    secret = _env_str("CURIO_SECRET_KEY")
    temporary = secret.lower() in _PLACEHOLDER_SECRETS
    if temporary:
        secret = secrets.token_urlsafe(48)
        logger.warning(
            "CURIO_SECRET_KEY is not set. A temporary key was generated; "
            "users will be logged out when the server restarts."
        )

    return Settings(
        environment=_env_str("CURIO_ENV", "development") or "development",
        debug=_env_bool("CURIO_DEBUG", False),
        secret_key=secret,
        secret_key_is_temporary=temporary,
        database_url=_env_str("CURIO_DATABASE_URL") or _default_database_url(),
        session_max_age=_env_int("CURIO_SESSION_MAX_AGE", 60 * 60 * 24 * 14),
        secure_cookies=_env_bool("CURIO_SECURE_COOKIES", False),
        http_timeout=_env_float("CURIO_HTTP_TIMEOUT", 8.0),
        tmdb_api_key=_env_str("TMDB_API_KEY"),
        tmdb_read_access_token=_env_str("TMDB_READ_ACCESS_TOKEN"),
        google_books_api_key=_env_str("GOOGLE_BOOKS_API_KEY"),
        itunes_country=(_env_str("ITUNES_COUNTRY", "US") or "US").upper()[:2],
    )
