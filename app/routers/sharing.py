"""Public share links for collections (enable/disable + public read-only view)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.csrf import verify_csrf
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.templating import flash, redirect, render
from app.database import get_db
from app.models import User
from app.services import pdf_export, sharing_service

router = APIRouter(include_in_schema=False)


@router.post("/collections/{collection_id}/share", dependencies=[Depends(verify_csrf)])
def share_collection(
    request: Request, collection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    collection = sharing_service.enable_sharing(db, user, collection_id)
    flash(request, f"Sharing is on for “{collection.name}”. Copy the link below to share it.")
    return redirect(f"/collections/{collection.id}")


@router.post("/collections/{collection_id}/unshare", dependencies=[Depends(verify_csrf)])
def unshare_collection(
    request: Request, collection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    collection = sharing_service.disable_sharing(db, user, collection_id)
    flash(request, f"Sharing is off for “{collection.name}”. The old link no longer works.", "info")
    return redirect(f"/collections/{collection.id}")


@router.get("/shared/{token}")
def shared_collection_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
    _viewer: User | None = Depends(get_current_user_optional),
) -> Response:
    """Public, read-only view of a shared collection (no login required)."""
    collection = sharing_service.get_shared_collection(db, token)
    context = {
        "collection": collection,
        "items": sharing_service.sorted_items(collection),
        "owner_name": collection.owner.name,
        "token": token,
    }
    response = render(request, "shared/collection.html", context)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@router.get("/shared/{token}/export.pdf")
def shared_collection_pdf(token: str, db: Session = Depends(get_db)) -> Response:
    """PDF of a shared collection; personal notes and tags are never included."""
    collection = sharing_service.get_shared_collection(db, token)
    pdf = pdf_export.build_items_pdf(
        title=collection.name,
        description=collection.description,
        owner_name=collection.owner.name,
        items=sharing_service.sorted_items(collection),
        include_private=False,
    )
    filename = pdf_export.safe_filename(collection.name)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "X-Robots-Tag": "noindex, nofollow"},
    )
