"""Shared helpers for ORM models."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite has no native time-zone support)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
