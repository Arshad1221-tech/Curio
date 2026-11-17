"""Dashboard page and statistics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.templating import render
from app.database import get_db
from app.models import User
from app.schemas.stats import DashboardStatsOut
from app.services import recommendation_service, stats_service

router = APIRouter(include_in_schema=False)
api_router = APIRouter(prefix="/api/stats", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    stats = stats_service.get_dashboard_stats(db, user)
    suggestions = recommendation_service.get_recommendations(db, user, limit=4) if stats.total_items else None
    context = {
        "active": "dashboard",
        "stats": stats,
        "suggestions": suggestions,
    }
    return render(request, "dashboard.html", context)


@api_router.get("", response_model=DashboardStatsOut)
def api_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DashboardStatsOut:
    """Collection counts and personal statistics for the signed-in user."""
    return DashboardStatsOut.from_stats(stats_service.get_dashboard_stats(db, user))
