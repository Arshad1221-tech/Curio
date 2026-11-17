"""Item pages (library, add/edit forms, detail) and item JSON endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.constants import MEDIA_TYPE_KEYS
from app.core.csrf import verify_csrf
from app.core.dependencies import get_current_user
from app.core.forms import validation_errors
from app.core.templating import flash, redirect, render
from app.database import get_db
from app.models import Item, User
from app.schemas.item import FavouriteOut, ItemIn, ItemOut
from app.services import collection_service, item_service, metadata_service
from app.services.item_service import ItemFilters

router = APIRouter(include_in_schema=False)
api_router = APIRouter(prefix="/api/items", tags=["items"])

ITEM_TEXT_FIELDS = (
    "media_type", "title", "creator", "release_year", "description", "genres", "tags", "keywords",
    "image_url", "external_source", "external_id", "external_url", "rating", "status", "notes",
)


@dataclass
class ItemFormData:
    values: dict[str, Any]
    collection_ids: list[int]


async def read_item_form(request: Request) -> ItemFormData:
    """Collect the raw item form fields (kept as strings so the form can be re-displayed)."""
    form = await request.form()
    values: dict[str, Any] = {}
    for name in ITEM_TEXT_FIELDS:
        raw = form.get(name)
        values[name] = raw if isinstance(raw, str) else ""
    favourite = form.get("is_favourite")
    values["is_favourite"] = isinstance(favourite, str) and favourite.strip().lower() in {"1", "true", "on", "yes"}
    collection_ids = [int(v) for v in form.getlist("collection_ids") if isinstance(v, str) and v.isdigit()]
    return ItemFormData(values=values, collection_ids=collection_ids)


def _values_from_item(item: Item) -> dict[str, Any]:
    return {
        "media_type": item.media_type,
        "title": item.title,
        "creator": item.creator or "",
        "release_year": item.release_year or "",
        "description": item.description or "",
        "genres": ", ".join(item.genre_list),
        "tags": ", ".join(item.tag_names),
        "keywords": ", ".join(item.keyword_list),
        "image_url": item.image_url or "",
        "external_source": item.external_source,
        "external_id": item.external_id or "",
        "external_url": item.external_url or "",
        "rating": item.rating or "",
        "status": item.status,
        "notes": item.notes or "",
        "is_favourite": item.is_favourite,
    }


def _render_form(
    request: Request,
    db: Session,
    user: User,
    *,
    values: dict[str, Any],
    selected_collections: list[int],
    errors: dict[str, str] | None = None,
    item: Item | None = None,
    status_code: int = 200,
) -> Response:
    context = {
        "active": "items",
        "values": values,
        "errors": errors or {},
        "item": item,
        "editing": item is not None,
        "collections": collection_service.list_collections(db, user),
        "selected_collections": set(selected_collections),
        "known_tags": [name for name, _ in item_service.tag_counts(db, user)],
        "lookup_unavailable": [t for t, ok in metadata_service.lookup_availability().items() if not ok],
    }
    return render(request, "items/form.html", context, status_code)


# --- Library ---------------------------------------------------------------------
@router.get("/items")
def library(
    request: Request,
    q: str = "",
    media_type: str = Query("", alias="type"),
    tag: str = "",
    genre: str = "",
    status: str = "",
    favourites: str = "",
    rating: str = "",
    sort: str = "",
    page: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    filters = ItemFilters.from_params(
        q=q, media_type=media_type, tag=tag, genre=genre, status=status,
        favourites=favourites, rating=rating, sort=sort, page=page,
    )
    counts = item_service.type_counts(db, user)
    context = {
        "active": "items",
        "filters": filters,
        "query": filters.as_query(),
        "result": item_service.list_items(db, user, filters),
        "type_counts": counts,
        "library_total": sum(counts.values()),
        "tags": item_service.tag_counts(db, user),
        "genres": item_service.genre_counts(db, user),
    }
    return render(request, "items/list.html", context)


# --- Create ----------------------------------------------------------------------
@router.get("/items/new")
def new_item_page(
    request: Request,
    media_type: str = Query("", alias="type"),
    collection: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    values = {"media_type": media_type if media_type in MEDIA_TYPE_KEYS else "book", "status": "completed"}
    selected = [int(collection)] if collection.isdigit() else []
    return _render_form(request, db, user, values=values, selected_collections=selected)


@router.post("/items/new", dependencies=[Depends(verify_csrf)])
def create_item(
    request: Request,
    form: ItemFormData = Depends(read_item_form),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    try:
        data = ItemIn(**form.values)
    except ValidationError as exc:
        return _render_form(
            request, db, user, values=form.values, selected_collections=form.collection_ids,
            errors=validation_errors(exc), status_code=400,
        )
    duplicate = item_service.find_duplicate(db, user, data.media_type, data.title, data.external_id)
    item = item_service.create_item(db, user, data, form.collection_ids)
    if duplicate:
        flash(request, f"Added “{item.title}”. Note: you already had a similar item in your library.", "warning")
    else:
        flash(request, f"“{item.title}” was added to your library.")
    return redirect(f"/items/{item.id}")


# --- Read / update / delete ------------------------------------------------------
@router.get("/items/{item_id}")
def item_detail(
    request: Request, item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    item = item_service.get_item(db, user, item_id)
    context = {
        "active": "items",
        "item": item,
        "collections": collection_service.list_collections(db, user),
        "member_ids": {c.id for c in item.collections},
    }
    return render(request, "items/detail.html", context)


@router.get("/items/{item_id}/edit")
def edit_item_page(
    request: Request, item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    item = item_service.get_item(db, user, item_id)
    return _render_form(
        request, db, user, values=_values_from_item(item),
        selected_collections=[c.id for c in item.collections], item=item,
    )


@router.post("/items/{item_id}/edit", dependencies=[Depends(verify_csrf)])
def update_item(
    request: Request,
    item_id: int,
    form: ItemFormData = Depends(read_item_form),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    item = item_service.get_item(db, user, item_id)
    try:
        data = ItemIn(**form.values)
    except ValidationError as exc:
        return _render_form(
            request, db, user, values=form.values, selected_collections=form.collection_ids,
            errors=validation_errors(exc), item=item, status_code=400,
        )
    item = item_service.update_item(db, user, item_id, data, form.collection_ids)
    flash(request, f"Your changes to “{item.title}” were saved.")
    return redirect(f"/items/{item.id}")


@router.post("/items/{item_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_item(
    request: Request, item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    title = item_service.delete_item(db, user, item_id)
    flash(request, f"“{title}” was removed from your library.", "info")
    return redirect("/items")


@router.post("/items/{item_id}/collections", dependencies=[Depends(verify_csrf)])
async def update_item_collections(
    request: Request, item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    form = await request.form()
    ids = [int(v) for v in form.getlist("collection_ids") if isinstance(v, str) and v.isdigit()]
    item = item_service.set_item_collections(db, user, item_id, ids)
    flash(request, f"Collections updated for “{item.title}”.")
    return redirect(f"/items/{item.id}")


# --- JSON API --------------------------------------------------------------------
@api_router.get("", response_model=list[ItemOut])
def api_list_items(
    q: str = "",
    media_type: str = Query("", alias="type"),
    tag: str = "",
    genre: str = "",
    favourites: str = "",
    sort: str = "",
    page: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Item]:
    """List the signed-in user's items with optional search and filters."""
    filters = ItemFilters.from_params(
        q=q, media_type=media_type, tag=tag, genre=genre, favourites=favourites, sort=sort, page=page
    )
    return item_service.list_items(db, user, filters).items


@api_router.get("/{item_id}", response_model=ItemOut)
def api_get_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Item:
    return item_service.get_item(db, user, item_id)


@api_router.post("/{item_id}/favourite", response_model=FavouriteOut, dependencies=[Depends(verify_csrf)])
def api_toggle_favourite(
    item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> FavouriteOut:
    """Toggle the favourite flag (used by the heart buttons in the interface)."""
    item = item_service.toggle_favourite(db, user, item_id)
    return FavouriteOut(id=item.id, is_favourite=item.is_favourite)
