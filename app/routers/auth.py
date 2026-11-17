"""Registration, login and logout pages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.csrf import verify_csrf
from app.core.dependencies import get_current_user_optional, login_user, logout_user
from app.core.errors import ConflictError
from app.core.forms import domain_error, validation_errors
from app.core.rate_limit import login_limiter
from app.core.templating import flash, redirect, render, safe_next_url
from app.database import get_db
from app.models import User
from app.schemas.user import UserCreate
from app.services import user_service

router = APIRouter(include_in_schema=False)


@router.get("/register")
def register_page(request: Request, user: User | None = Depends(get_current_user_optional)) -> Response:
    if user:
        return redirect("/dashboard")
    return render(request, "auth/register.html", {"values": {}, "errors": {}})


@router.post("/register", dependencies=[Depends(verify_csrf)])
def register(
    request: Request,
    username: str = Form(""),
    email: str = Form(""),
    display_name: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
    _current: User | None = Depends(get_current_user_optional),
) -> Response:
    values = {"username": username, "email": email, "display_name": display_name}
    try:
        data = UserCreate(
            username=username,
            email=email,
            display_name=display_name,
            password=password,
            confirm_password=confirm_password,
        )
        user = user_service.register_user(db, data)
    except ValidationError as exc:
        return render(request, "auth/register.html", {"values": values, "errors": validation_errors(exc)}, 400)
    except ConflictError as exc:
        return render(request, "auth/register.html", {"values": values, "errors": domain_error(exc)}, 400)

    login_user(request, user)
    flash(request, f"Welcome to Curio, {user.name}! Start by adding something you love.")
    return redirect("/dashboard")


@router.get("/login")
def login_page(
    request: Request,
    next_url: str | None = Query(None, alias="next"),
    user: User | None = Depends(get_current_user_optional),
) -> Response:
    if user:
        return redirect(safe_next_url(next_url))
    return render(request, "auth/login.html", {"values": {}, "errors": {}, "next_url": safe_next_url(next_url)})


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login(
    request: Request,
    identifier: str = Form(""),
    password: str = Form(""),
    next_url: str = Form("", alias="next"),
    db: Session = Depends(get_db),
    _current: User | None = Depends(get_current_user_optional),
) -> Response:
    destination = safe_next_url(next_url)
    context = {"values": {"identifier": identifier}, "next_url": destination}

    if not identifier.strip() or not password:
        context["errors"] = {"__all__": "Enter your username or email and your password."}
        return render(request, "auth/login.html", context, 400)

    limiter_key = login_limiter.key(request.client.host if request.client else None, identifier)
    if login_limiter.is_blocked(limiter_key):
        context["errors"] = {"__all__": "Too many failed attempts. Please wait a few minutes and try again."}
        return render(request, "auth/login.html", context, 429)

    user = user_service.authenticate(db, identifier, password)
    if user is None:
        login_limiter.record_failure(limiter_key)
        context["errors"] = {"__all__": "Incorrect username/email or password."}
        return render(request, "auth/login.html", context, 400)

    login_limiter.reset(limiter_key)
    login_user(request, user)
    flash(request, f"Welcome back, {user.name}!")
    return redirect(destination)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request) -> Response:
    logout_user(request)
    flash(request, "You have been logged out. See you soon!", "info")
    return redirect("/")
