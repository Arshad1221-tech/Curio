"""User profile management: details, password and account deletion."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.csrf import verify_csrf
from app.core.dependencies import get_current_user, logout_user
from app.core.errors import CurioError
from app.core.forms import domain_error, validation_errors
from app.core.templating import flash, redirect, render
from app.database import get_db
from app.models import User
from app.schemas.user import PasswordChange, ProfileUpdate, UserOut
from app.services import user_service

router = APIRouter(include_in_schema=False)
api_router = APIRouter(prefix="/api", tags=["profile"])


def _render_profile(request: Request, db: Session, user: User, status_code: int = 200, **extra: Any) -> Response:
    context: dict[str, Any] = {
        "active": "profile",
        "summary": user_service.account_summary(db, user),
        "values": {"display_name": user.display_name or "", "email": user.email, "bio": user.bio or ""},
        "profile_errors": {},
        "password_errors": {},
        "delete_errors": {},
    }
    context.update(extra)
    return render(request, "profile/profile.html", context, status_code)


@router.get("/profile")
def profile_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    return _render_profile(request, db, user)


@router.post("/profile", dependencies=[Depends(verify_csrf)])
def update_profile(
    request: Request,
    display_name: str = Form(""),
    email: str = Form(""),
    bio: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    values = {"display_name": display_name, "email": email, "bio": bio}
    try:
        user_service.update_profile(db, user, ProfileUpdate(display_name=display_name, email=email, bio=bio))
    except ValidationError as exc:
        return _render_profile(request, db, user, 400, values=values, profile_errors=validation_errors(exc))
    except CurioError as exc:
        return _render_profile(request, db, user, 400, values=values, profile_errors=domain_error(exc))
    flash(request, "Your profile has been updated.")
    return redirect("/profile")


@router.post("/profile/password", dependencies=[Depends(verify_csrf)])
def change_password(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    try:
        data = PasswordChange(
            current_password=current_password, new_password=new_password, confirm_password=confirm_password
        )
        user_service.change_password(db, user, data)
    except ValidationError as exc:
        return _render_profile(request, db, user, 400, password_errors=validation_errors(exc))
    except CurioError as exc:
        return _render_profile(request, db, user, 400, password_errors=domain_error(exc))
    flash(request, "Your password has been changed.")
    return redirect("/profile")


@router.post("/profile/delete", dependencies=[Depends(verify_csrf)])
def delete_account(
    request: Request,
    delete_password: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    try:
        user_service.delete_account(db, user, delete_password)
    except CurioError as exc:
        return _render_profile(request, db, user, 400, delete_errors=domain_error(exc))
    logout_user(request)
    flash(request, "Your account and all of its data have been permanently deleted.", "info")
    return redirect("/")


@api_router.get("/me", response_model=UserOut)
def read_current_user(user: User = Depends(get_current_user)) -> User:
    """Return the signed-in user's profile."""
    return user
