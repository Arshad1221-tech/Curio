"""PDF downloads of a user's collections and whole library."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.services import collection_service, item_service, pdf_export, sharing_service

router = APIRouter(tags=["export"])


def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@router.get("/collections/{collection_id}/export.pdf", response_class=Response)
def export_collection(collection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    """Download one collection as a PDF (includes your notes and tags)."""
    collection = collection_service.get_collection(db, user, collection_id)
    pdf = pdf_export.build_items_pdf(
        title=collection.name,
        description=collection.description,
        owner_name=user.name,
        items=sharing_service.sorted_items(collection),
    )
    return _pdf_response(pdf, pdf_export.safe_filename(collection.name))


@router.get("/export/library.pdf", response_class=Response)
def export_library(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    """Download the whole library as a PDF."""
    pdf = pdf_export.build_items_pdf(
        title=f"{user.name}'s library",
        description="Every book, film, show, song and album in your Curio library.",
        owner_name=user.name,
        items=item_service.all_items(db, user),
    )
    return _pdf_response(pdf, pdf_export.safe_filename(f"{user.username}-library", "library"))
