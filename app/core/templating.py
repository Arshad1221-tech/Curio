"""Jinja2 template configuration, flash messages and rendering helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME, TAGLINE, TEMPLATES_DIR
from app.core.constants import (
    EXTERNAL_SOURCES,
    MEDIA_TYPES,
    SORT_OPTIONS,
    SQUARE_ARTWORK_TYPES,
    STATUSES,
)
from app.core.csrf import get_csrf_token

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

FLASH_KEY = "_flashes"


# --- Template filters and globals --------------------------------------------
def _format_date(value: datetime | None, fmt: str = "%d %b %Y") -> str:
    return value.strftime(fmt) if value else ""


def _media_meta(media_type: str | None) -> dict[str, str]:
    return MEDIA_TYPES.get(media_type or "other", MEDIA_TYPES["other"])


def _query_string(params: dict[str, Any] | None = None, **overrides: Any) -> str:
    """Build ``?a=1&b=2`` from current filter values, dropping empty entries."""
    merged: dict[str, Any] = dict(params or {})
    merged.update(overrides)
    clean = {k: v for k, v in merged.items() if v not in (None, "", False, [])}
    return f"?{urlencode(clean, doseq=True)}" if clean else ""


templates.env.globals.update(
    app_name=APP_NAME,
    tagline=TAGLINE,
    MEDIA_TYPES=MEDIA_TYPES,
    STATUSES=STATUSES,
    SORT_OPTIONS=SORT_OPTIONS,
    EXTERNAL_SOURCES=EXTERNAL_SOURCES,
    SQUARE_ARTWORK_TYPES=SQUARE_ARTWORK_TYPES,
    media_meta=_media_meta,
    query_string=_query_string,
    current_year=lambda: datetime.now().year,
)
templates.env.filters["datefmt"] = _format_date


# --- Flash messages ------------------------------------------------------------
def flash(request: Request, message: str, category: str = "success") -> None:
    """Queue a one-time message shown on the next rendered page."""
    if "session" not in request.scope:
        return
    messages = list(request.session.get(FLASH_KEY, []))
    messages.append({"message": message, "category": category})
    request.session[FLASH_KEY] = messages


def _pop_flashes(request: Request) -> list[dict[str, str]]:
    if "session" not in request.scope:
        return []
    return request.session.pop(FLASH_KEY, [])


# --- Rendering -----------------------------------------------------------------
def render(
    request: Request,
    template_name: str,
    context: dict[str, Any] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Render a template with the shared context every page needs."""
    base_context: dict[str, Any] = {
        "request": request,
        "user": getattr(request.state, "user", None),
        "csrf_token": get_csrf_token(request),
        "flashes": _pop_flashes(request),
    }
    base_context.update(context or {})
    return templates.TemplateResponse(request, template_name, base_context, status_code=status_code)


def redirect(url: str, status_code: int = 303) -> RedirectResponse:
    """Post/Redirect/Get helper (303 forces the browser to issue a GET)."""
    return RedirectResponse(url=url, status_code=status_code)


def safe_next_url(value: str | None, default: str = "/dashboard") -> str:
    """Only allow local redirects to prevent open-redirect attacks."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return default
