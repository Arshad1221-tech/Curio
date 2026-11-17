"""FastAPI dependencies for authentication and session handling."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.csrf import rotate_csrf_token
from app.core.errors import LoginRequired
from app.database import get_db
from app.models import User

SESSION_USER_KEY = "user_id"


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Return the signed-in user, or ``None`` for anonymous visitors."""
    user_id = request.session.get(SESSION_USER_KEY)
    user = db.get(User, user_id) if isinstance(user_id, int) else None
    if user_id is not None and user is None:
        # The account no longer exists (e.g. deleted in another tab).
        request.session.pop(SESSION_USER_KEY, None)
    request.state.user = user
    return user


def get_current_user(request: Request, user: User | None = Depends(get_current_user_optional)) -> User:
    """Require a signed-in user; anonymous visitors are sent to the login page."""
    if user is None:
        if request.method == "GET":
            next_url = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        else:
            next_url = "/dashboard"
        raise LoginRequired(next_url)
    return user


def login_user(request: Request, user: User) -> None:
    """Start a fresh session for ``user`` (prevents session fixation)."""
    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id
    rotate_csrf_token(request)
    request.state.user = user


def logout_user(request: Request) -> None:
    request.session.clear()
    rotate_csrf_token(request)
    request.state.user = None
