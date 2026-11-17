"""Optional demo account for presentations (``python -m scripts.init_db --demo``).

The demo password below is intentionally public and documented in the README.
Do not create the demo account on a publicly reachable deployment.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.collection import CollectionIn
from app.schemas.item import ItemIn
from app.schemas.user import UserCreate
from app.services import collection_service, item_service, sharing_service, user_service
from app.services.recommendation_service import load_catalogue

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@curio.local"
DEMO_PASSWORD = "CurioDemo123"

# (title, media_type, rating, favourite, tags, status, note)
DEMO_ITEMS = [
    ("Dune", "book", 5, True, ["space opera", "reread"], "completed", "The world-building still amazes me."),
    ("The Hobbit", "book", 4, False, ["comfort read"], "completed", None),
    ("Project Hail Mary", "book", None, False, ["space opera"], "wishlist", "Recommended by a friend."),
    ("Interstellar", "movie", 5, True, ["mind-bending", "soundtrack"], "completed", "That docking scene!"),
    ("Arrival", "movie", 4, False, ["mind-bending"], "completed", None),
    ("Toy Story", "movie", 3, False, ["family night"], "completed", None),
    ("Stranger Things", "tv", 4, True, ["binge-worthy"], "in_progress", "Currently on season 3."),
    ("Sherlock", "tv", 4, False, ["detective"], "completed", None),
    ("Bohemian Rhapsody", "song", 5, True, ["road trip"], "completed", None),
    ("Blinding Lights", "song", 4, False, ["workout"], "completed", None),
    ("Kind of Blue", "album", 4, False, ["focus"], "completed", "Perfect background for studying."),
]

DEMO_COLLECTIONS = [
    ("Sci-fi favourites", "Stories that make me look up at the stars.", ["Dune", "Interstellar", "Arrival", "Project Hail Mary"], True),
    ("Feel-good evenings", "Comfort picks for a relaxed night in.", ["The Hobbit", "Toy Story", "Bohemian Rhapsody"], False),
]


def create_demo_account(db: Session) -> tuple[bool, str]:
    """Create the demo user with sample items and collections. Returns (created, message)."""
    if user_service.get_user_by_username(db, DEMO_USERNAME):
        return False, f"Demo account already exists (username: {DEMO_USERNAME})."

    user = user_service.register_user(
        db,
        UserCreate(
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            display_name="Demo Curator",
            password=DEMO_PASSWORD,
            confirm_password=DEMO_PASSWORD,
        ),
    )

    catalogue = {(c.media_type, c.title): c for c in load_catalogue()}
    created: dict[str, int] = {}
    for title, media_type, rating, favourite, tags, status, note in DEMO_ITEMS:
        source = catalogue.get((media_type, title))
        if source is None:
            continue
        item = item_service.create_item(
            db,
            user,
            ItemIn(
                media_type=media_type,
                title=title,
                creator=source.creator,
                release_year=source.release_year,
                description=source.description,
                genres=source.genres,
                keywords=source.keywords,
                tags=tags,
                rating=rating,
                is_favourite=favourite,
                status=status,
                notes=note,
                external_source="catalogue",
                external_id=source.external_id,
            ),
        )
        created[title] = item.id

    for name, description, titles, shared in DEMO_COLLECTIONS:
        collection = collection_service.create_collection(db, user, CollectionIn(name=name, description=description))
        collection_service.add_items(db, user, collection.id, [created[t] for t in titles if t in created])
        if shared:
            sharing_service.enable_sharing(db, user, collection.id)

    return True, f"Demo account created - username: {DEMO_USERNAME} / password: {DEMO_PASSWORD}"
