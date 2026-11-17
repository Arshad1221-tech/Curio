"""Cross-Site Request Forgery (CSRF) protection.

A random token is stored in the signed session cookie. Every state-changing
request must echo it back, either as a ``csrf_token`` form field or as an
``X-CSRF-Token`` header (used by JavaScript ``fetch`` calls).
"""

from __future__ import annotations

import hmac
import secrets

from fastapi import HTTPException, Request, status

SESSION_KEY = "csrf_token"
HEADER_NAME = "X-CSRF-Token"
FORM_FIELD = "csrf_token"


def get_csrf_token(request: Request) -> str:
    """Return the session's CSRF token, creating one if necessary."""
    if "session" not in request.scope:
        return ""
    token = request.session.get(SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[SESSION_KEY] = token
    return token


def rotate_csrf_token(request: Request) -> str:
    """Issue a fresh token (called after login/logout)."""
    token = secrets.token_urlsafe(32)
    request.session[SESSION_KEY] = token
    return token


async def verify_csrf(request: Request) -> None:
    """FastAPI dependency that rejects requests without a valid CSRF token."""
    expected = request.session.get(SESSION_KEY)
    supplied = request.headers.get(HEADER_NAME)

    if not supplied:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()  # Starlette caches the parsed form for the route
            value = form.get(FORM_FIELD)
            supplied = value if isinstance(value, str) else None

    if not expected or not supplied or not hmac.compare_digest(str(expected), str(supplied)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your session expired or the form could not be verified. Please refresh the page and try again.",
        )
