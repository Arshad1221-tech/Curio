"""Personalised recommendations ("Discover") page and JSON endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.constants import MEDIA_TYPE_KEYS
from app.core.csrf import verify_csrf
from app.core.dependencies import get_current_user
from app.core.forms import validation_errors
from app.core.templating import flash, redirect, render, safe_next_url
from app.database import get_db
from app.models import User
from app.schemas.item import ItemIn
from app.schemas.recommendation import RecommendationListOut, RecommendationOut
from app.services import item_service, metadata_service, recommendation_service

router = APIRouter(include_in_schema=False)
api_router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

SAVE_FIELDS = (
    "media_type", "title", "creator", "release_year", "description", "genres", "keywords",
    "image_url", "external_source", "external_id", "external_url",
)


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "on", "yes"}


@router.get("/recommendations")
def recommendations_page(
    request: Request,
    media_type: str = Query("", alias="type"),
    online: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    selected_type = media_type if media_type in MEDIA_TYPE_KEYS else ""
    result = recommendation_service.get_recommendations(
        db, user, media_type=selected_type or None, include_online=_truthy(online)
    )
    statuses = metadata_service.source_statuses()
    context = {
        "active": "recommendations",
        "result": result,
        "selected_type": selected_type,
        "online": _truthy(online),
        "tmdb_enabled": any(s.key == "tmdb" and s.enabled for s in statuses),
        "query": {"type": selected_type, "online": "1" if _truthy(online) else ""},
    }
    return render(request, "recommendations/index.html", context)


@router.post("/recommendations/save", dependencies=[Depends(verify_csrf)])
async def save_recommendation(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """Add a recommended title to the library as a wishlist item."""
    form = await request.form()
    values = {name: (form.get(name) if isinstance(form.get(name), str) else "") for name in SAVE_FIELDS}
    values["status"] = "wishlist"
    back = safe_next_url(form.get("next") if isinstance(form.get("next"), str) else None, "/recommendations")
    try:
        data = ItemIn(**values)
    except ValidationError as exc:
        first_error = next(iter(validation_errors(exc).values()), "Invalid recommendation data.")
        flash(request, f"Couldn't save that suggestion: {first_error}", "danger")
        return redirect(back)

    existing = item_service.find_duplicate(db, user, data.media_type, data.title, data.external_id)
    if existing:
        flash(request, f"“{existing.title}” is already in your library.", "info")
        return redirect(back)

    item = item_service.create_item(db, user, data)
    flash(request, f"“{item.title}” was added to your wishlist.")
    return redirect(back)


@api_router.get("", response_model=RecommendationListOut)
def api_recommendations(
    media_type: str = Query("", alias="type"),
    online: bool = False,
    limit: int = Query(24, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecommendationListOut:
    """Ranked recommendations for the signed-in user."""
    selected = media_type if media_type in MEDIA_TYPE_KEYS else None
    result = recommendation_service.get_recommendations(db, user, media_type=selected, include_online=online, limit=limit)
    return RecommendationListOut(
        cold_start=result.cold_start,
        library_size=result.library_size,
        online_used=result.online_used,
        online_errors=result.online_errors,
        recommendations=[RecommendationOut.from_recommendation(r) for r in result.recommendations],
    )
