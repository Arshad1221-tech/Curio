from app.services.recommendation_engine import (
    ContentItem,
    build_profile,
    preference_weight,
    recommend,
    starter_picks,
)


def make(title, media_type="movie", genres=(), creator=None, tags=(), keywords=(), rating=None, fav=False, **kw):
    return ContentItem(
        media_type=media_type,
        title=title,
        creator=creator,
        genres=list(genres),
        tags=list(tags),
        keywords=list(keywords),
        rating=rating,
        is_favourite=fav,
        **kw,
    )


CANDIDATES = [
    make("Arrival", genres=["Science Fiction", "Drama"], creator="Denis Villeneuve", keywords=["aliens", "language"]),
    make("Notting Hill", genres=["Romance", "Comedy"], creator="Roger Michell"),
    make("The Dark Knight", genres=["Action", "Crime"], creator="Christopher Nolan"),
    make("Dune", media_type="book", genres=["Science Fiction"], creator="Frank Herbert", keywords=["desert"]),
]


def test_preference_weight_orders_ratings():
    assert preference_weight(1, False) < 0 < preference_weight(3, False) < preference_weight(5, False)
    assert preference_weight(5, True) > preference_weight(5, False)
    assert preference_weight(None, False) == 1.0


def test_recommends_items_matching_liked_genres_first():
    library = [
        make("Interstellar", genres=["Sci-Fi", "Drama"], creator="Christopher Nolan", rating=5, fav=True),
        make("Blade Runner 2049", genres=["Science Fiction"], creator="Denis Villeneuve", rating=4),
    ]
    results = recommend(library, CANDIDATES, limit=10)
    titles = [r.item.title for r in results]
    assert titles[0] == "Arrival"  # shares genre AND director
    assert "Notting Hill" not in titles  # no shared meaningful features
    assert results[0].match_percent == 95
    assert any("Science Fiction" in reason for reason in results[0].reasons)


def test_owned_items_are_excluded():
    library = [make("Arrival", genres=["Science Fiction"], rating=5)]
    titles = [r.item.title for r in recommend(library, CANDIDATES)]
    assert "Arrival" not in titles


def test_low_ratings_push_matching_candidates_down():
    library = [
        make("Love Actually", genres=["Romance", "Comedy"], rating=1),
        make("Alien", genres=["Science Fiction", "Horror"], rating=5),
    ]
    titles = [r.item.title for r in recommend(library, CANDIDATES)]
    assert "Notting Hill" not in titles
    assert "Arrival" in titles


def test_media_type_filter():
    library = [make("Foundation", media_type="book", genres=["Science Fiction"], rating=5)]
    results = recommend(library, CANDIDATES, media_type="book")
    assert [r.item.title for r in results] == ["Dune"]


def test_profile_requires_positive_preferences():
    library = [make("Bad Movie", genres=["Horror"], rating=1)]
    assert recommend(library, CANDIDATES) == []
    assert build_profile(library)["genre:horror"] < 0


def test_starter_picks_for_cold_start():
    pool = [make("A", starter=True), make("B"), make("C", media_type="book", starter=True)]
    assert [r.item.title for r in starter_picks(pool)] == ["A", "C"]
    assert [r.item.title for r in starter_picks(pool, media_type="book")] == ["C"]
