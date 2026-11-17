"""Helpers for turning validation errors into per-field form messages."""

from __future__ import annotations

from pydantic import ValidationError

from app.core.errors import CurioError


def _humanise(message: str) -> str:
    message = message.removeprefix("Value error, ").removeprefix("Assertion failed, ")
    return message[:1].upper() + message[1:] if message else "Invalid value"


def validation_errors(exc: ValidationError) -> dict[str, str]:
    """Map a Pydantic ``ValidationError`` to ``{field_name: message}``."""
    errors: dict[str, str] = {}
    for error in exc.errors():
        location = error.get("loc") or ()
        field = str(location[0]) if location else "__all__"
        errors.setdefault(field, _humanise(str(error.get("msg", ""))))
    return errors


def domain_error(exc: CurioError) -> dict[str, str]:
    """Map a service-layer error to a form error dictionary."""
    return {exc.field or "__all__": exc.message}
