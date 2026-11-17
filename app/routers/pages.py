"""Public marketing pages."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.templating import render

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def landing(request: Request) -> HTMLResponse:
    """Landing page with the Curio name and tagline."""
    return render(request, "landing.html", {"active": "home"})
