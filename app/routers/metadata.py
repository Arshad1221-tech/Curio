"""JSON endpoints that proxy TMDB, Google Books and iTunes lookups.

Requests go through the server so API keys never reach the browser.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.constants import MEDIA_TYPE_KEYS
from app.core.dependencies import get_current_user
from app.core.errors import CurioError
from app.models import User
from app.schemas.metadata import MetadataResult, MetadataSearchResponse, MetadataSourceStatus
from app.services import metadata_service

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.get("/sources", response_model=list[MetadataSourceStatus])
def list_sources(_user: User = Depends(get_current_user)) -> list[MetadataSourceStatus]:
    """Which metadata providers are configured."""
    return metadata_service.source_statuses()


@router.get("/search", response_model=MetadataSearchResponse)
def search_metadata(
    media_type: str = Query(..., alias="type", description="book, movie, tv, song or album"),
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(10, ge=1, le=20),
    _user: User = Depends(get_current_user),
) -> MetadataSearchResponse:
    """Search the provider that matches ``type`` and return normalised results."""
    if media_type not in MEDIA_TYPE_KEYS or media_type not in metadata_service.SOURCE_FOR_TYPE:
        raise CurioError("Online lookup isn't available for this type.")
    results = metadata_service.search(media_type, q, limit)
    return MetadataSearchResponse(
        source=metadata_service.SOURCE_FOR_TYPE[media_type],  # type: ignore[arg-type]
        query=q,
        results=results,
    )


@router.get("/details", response_model=MetadataResult)
def metadata_details(
    media_type: str = Query(..., alias="type"),
    source: str = Query(...),
    external_id: str = Query(..., alias="id", max_length=64),
    _user: User = Depends(get_current_user),
) -> MetadataResult:
    """Full details (director/creator, genres, keywords) for one result."""
    return metadata_service.details(media_type, source, external_id)
