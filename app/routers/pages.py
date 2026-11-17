"""Public marketing pages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.core.dependencies import get_current_user_optional
from app.core.templating import render
from app.models import User

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def landing(request: Request, _user: User | None = Depends(get_current_user_optional)) -> HTMLResponse:
    """Landing page with the Curio name and tagline."""
    return render(request, "landing.html", {"active": "home"})
