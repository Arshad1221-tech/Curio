"""Collection pages and JSON endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.csrf import verify_csrf
from app.core.dependencies import get_current_user
from app.core.errors import ConflictError
from app.core.forms import domain_error, validation_errors
from app.core.templating import flash, redirect, render
from app.database import get_db
from app.models import Collection, User
from app.schemas.collection import CollectionIn, CollectionOut
from app.services import collection_service, item_service
from app.services.item_service import ItemFilters

router = APIRouter(include_in_schema=False)
api_router = APIRouter(prefix="/api/collections", tags=["collections"])


def _render_list(request: Request, db: Session, user: User, status_code: int = 200, **extra) -> Response:
    context = {
        "active": "collections",
        "collections": collection_service.list_collections(db, user),
        "values": {},
        "errors": {},
        "open_create": False,
    }
    context.update(extra)
    return render(request, "collections/list.html", context, status_code)


def _render_detail(
    request: Request,
    db: Session,
    user: User,
    collection: Collection,
    *,
    media_type: str = "",
    sort: str = "",
    page: str = "",
    status_code: int = 200,
    **extra,
) -> Response:
    filters = ItemFilters.from_params(media_type=media_type, sort=sort or "title", page=page, collection_id=collection.id)
    context = {
        "active": "collections",
        "collection": collection,
        "filters": filters,
        "query": filters.as_query(),
        "result": item_service.list_items(db, user, filters),
        "available_items": collection_service.items_not_in_collection(db, user, collection),
        "values": {"name": collection.name, "description": collection.description or ""},
        "errors": {},
        "open_edit": False,
        "share_url": str(request.base_url).rstrip("/") + f"/shared/{collection.share_token}"
        if collection.share_token
        else None,
    }
    context.update(extra)
    return render(request, "collections/detail.html", context, status_code)


@router.get("/collections")
def collections_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    return _render_list(request, db, user)


@router.post("/collections", dependencies=[Depends(verify_csrf)])
def create_collection(
    request: Request,
    name: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    values = {"name": name, "description": description}
    try:
        collection = collection_service.create_collection(db, user, CollectionIn(name=name, description=description))
    except ValidationError as exc:
        return _render_list(request, db, user, 400, values=values, errors=validation_errors(exc), open_create=True)
    except ConflictError as exc:
        return _render_list(request, db, user, 400, values=values, errors=domain_error(exc), open_create=True)
    flash(request, f"Collection “{collection.name}” created. Add some items to it!")
    return redirect(f"/collections/{collection.id}")


@router.get("/collections/{collection_id}")
def collection_detail(
    request: Request,
    collection_id: int,
    media_type: str = Query("", alias="type"),
    sort: str = "",
    page: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    collection = collection_service.get_collection(db, user, collection_id)
    return _render_detail(request, db, user, collection, media_type=media_type, sort=sort, page=page)


@router.post("/collections/{collection_id}/edit", dependencies=[Depends(verify_csrf)])
def edit_collection(
    request: Request,
    collection_id: int,
    name: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    collection = collection_service.get_collection(db, user, collection_id)
    values = {"name": name, "description": description}
    try:
        collection = collection_service.update_collection(
            db, user, collection_id, CollectionIn(name=name, description=description)
        )
    except ValidationError as exc:
        return _render_detail(request, db, user, collection, status_code=400, values=values,
                              errors=validation_errors(exc), open_edit=True)
    except ConflictError as exc:
        return _render_detail(request, db, user, collection, status_code=400, values=values,
                              errors=domain_error(exc), open_edit=True)
    flash(request, "Collection updated.")
    return redirect(f"/collections/{collection.id}")


@router.post("/collections/{collection_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_collection(
    request: Request, collection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    name = collection_service.delete_collection(db, user, collection_id)
    flash(request, f"Collection “{name}” was deleted. Its items are still in your library.", "info")
    return redirect("/collections")


@router.post("/collections/{collection_id}/items", dependencies=[Depends(verify_csrf)])
async def add_items_to_collection(
    request: Request, collection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    form = await request.form()
    ids = [int(v) for v in form.getlist("item_ids") if isinstance(v, str) and v.isdigit()]
    added = collection_service.add_items(db, user, collection_id, ids)
    if added:
        flash(request, f"Added {added} item{'s' if added != 1 else ''} to the collection.")
    else:
        flash(request, "No new items were selected.", "info")
    return redirect(f"/collections/{collection_id}")


@router.post("/collections/{collection_id}/items/{item_id}/remove", dependencies=[Depends(verify_csrf)])
def remove_item_from_collection(
    request: Request,
    collection_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    title = collection_service.remove_item(db, user, collection_id, item_id)
    flash(request, f"Removed “{title}” from this collection.", "info")
    return redirect(f"/collections/{collection_id}")


# --- JSON API --------------------------------------------------------------------
@api_router.get("", response_model=list[CollectionOut])
def api_list_collections(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Collection]:
    """List the signed-in user's collections."""
    return collection_service.list_collections(db, user)
