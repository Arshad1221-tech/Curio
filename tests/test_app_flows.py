"""End-to-end tests of the main user journeys using FastAPI's TestClient."""

import re

from tests.conftest import extract_csrf


def _create_item(client, **overrides):
    token = extract_csrf(client.get("/items/new").text)
    data = {
        "csrf_token": token,
        "media_type": "movie",
        "title": "Interstellar",
        "creator": "Christopher Nolan",
        "release_year": "2014",
        "genres": "Sci-Fi, Drama",
        "tags": "Space, rewatch",
        "rating": "5",
        "status": "completed",
        "is_favourite": "1",
        "notes": "Docking scene!",
    }
    data.update(overrides)
    return client.post("/items/new", data=data, follow_redirects=False)


def test_landing_page_shows_brand_and_tagline(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Curio" in response.text
    assert "Collect what you love. Discover what’s next." in response.text


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_protected_pages_redirect_to_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=/dashboard")
    assert client.get("/api/items").status_code == 401


def test_register_validation_errors(client, csrf):
    response = client.post(
        "/register",
        data={"csrf_token": csrf("/register"), "username": "x", "email": "bad", "password": "short", "confirm_password": "nope"},
    )
    assert response.status_code == 400
    assert "Enter a valid email address" in response.text


def test_post_without_csrf_is_rejected(client):
    response = client.post("/login", data={"identifier": "a", "password": "b"})
    assert response.status_code == 403


def test_login_logout_cycle(logged_in, csrf):
    client = logged_in
    assert client.get("/dashboard").status_code == 200
    client.post("/logout", data={"csrf_token": csrf("/dashboard")})
    assert client.get("/dashboard", follow_redirects=False).status_code == 303

    bad = client.post("/login", data={"csrf_token": csrf(), "identifier": "alice", "password": "wrong-pass1"})
    assert bad.status_code == 400
    good = client.post(
        "/login", data={"csrf_token": csrf(), "identifier": "alice@example.com", "password": "Password123"},
        follow_redirects=False,
    )
    assert good.status_code == 303


def test_item_crud_search_and_favourite(logged_in):
    client = logged_in
    response = _create_item(client)
    assert response.status_code == 303
    item_url = response.headers["location"]
    item_id = int(item_url.rsplit("/", 1)[1])

    detail = client.get(item_url)
    assert "Interstellar" in detail.text and "Science Fiction" in detail.text and "#space" in detail.text

    assert "Interstellar" in client.get("/items?q=nolan").text
    assert "No items match" in client.get("/items?q=zzzz").text
    assert "Interstellar" in client.get("/items?genre=Science+Fiction").text
    assert "Interstellar" in client.get("/items?tag=space&favourites=1&rating=5").text

    api_item = client.get(f"/api/items/{item_id}").json()
    assert api_item["genres"] == ["Science Fiction", "Drama"]
    assert api_item["tags"] == ["rewatch", "space"]

    token = extract_csrf(detail.text)
    toggled = client.post(f"/api/items/{item_id}/favourite", headers={"X-CSRF-Token": token}).json()
    assert toggled == {"id": item_id, "is_favourite": False}

    edit_token = extract_csrf(client.get(f"{item_url}/edit").text)
    response = client.post(
        f"{item_url}/edit",
        data={"csrf_token": edit_token, "media_type": "movie", "title": "Interstellar (2014)", "rating": "4", "genres": "Drama"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert client.get(f"/api/items/{item_id}").json()["title"] == "Interstellar (2014)"

    delete_token = extract_csrf(client.get(item_url).text)
    client.post(f"{item_url}/delete", data={"csrf_token": delete_token})
    assert client.get(item_url).status_code == 404


def test_item_validation_rerenders_form(logged_in):
    response = _create_item(logged_in, title="   ", rating="9", image_url="not-a-url")
    assert response.status_code == 400
    assert "Title is required" in response.text


def test_collections_sharing_and_pdf(logged_in):
    client = logged_in
    item_id = int(_create_item(client).headers["location"].rsplit("/", 1)[1])

    token = extract_csrf(client.get("/collections").text)
    response = client.post("/collections", data={"csrf_token": token, "name": "Space night"}, follow_redirects=False)
    assert response.status_code == 303
    collection_url = response.headers["location"]

    duplicate = client.post("/collections", data={"csrf_token": token, "name": "space NIGHT"})
    assert duplicate.status_code == 400

    client.post(f"{collection_url}/items", data={"csrf_token": token, "item_ids": str(item_id)})
    page = client.get(collection_url)
    assert "Interstellar" in page.text

    pdf = client.get(f"{collection_url}/export.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    client.post(f"{collection_url}/share", data={"csrf_token": token})
    page = client.get(collection_url).text
    share_url = re.search(r'id="share-url"[^>]*value="([^"]+)"', page).group(1)
    share_path = share_url.split("://", 1)[1].split("/", 1)[1]

    client.cookies.clear()  # anonymous visitor
    public = client.get(f"/{share_path}")
    assert public.status_code == 200
    assert "Interstellar" in public.text
    assert "Docking scene!" not in public.text  # private notes are never shown
    assert client.get(f"/{share_path}/export.pdf").content.startswith(b"%PDF")
    assert client.get("/shared/not-a-real-token-123456").status_code == 404


def test_library_pdf_and_stats(logged_in):
    client = logged_in
    _create_item(client)
    _create_item(client, title="Dune", media_type="book", creator="Frank Herbert", genres="Science Fiction", rating="4", is_favourite="")
    stats = client.get("/api/stats").json()
    assert stats["total_items"] == 2
    assert stats["type_counts"]["book"] == 1
    assert stats["favourites_count"] == 1
    assert stats["average_rating"] == 4.5
    assert "Welcome back" in client.get("/dashboard").text
    assert client.get("/export/library.pdf").content.startswith(b"%PDF")


def test_recommendations_page_and_save(logged_in):
    client = logged_in
    _create_item(client)
    _create_item(client, title="Blade Runner", genres="Science Fiction, Thriller", rating="4", creator="Ridley Scott")
    _create_item(client, title="Alien", genres="Science Fiction, Horror", rating="5", creator="Ridley Scott")

    data = client.get("/api/recommendations").json()
    assert data["cold_start"] is False
    assert data["recommendations"], "expected catalogue recommendations"
    top = data["recommendations"][0]
    assert top["reasons"]

    page = client.get("/recommendations")
    assert "Recommended for you" in page.text
    token = extract_csrf(page.text)
    response = client.post(
        "/recommendations/save",
        data={"csrf_token": token, "media_type": top["media_type"], "title": top["title"],
              "genres": ",".join(top["genres"]), "external_source": "catalogue", "external_id": top["external_id"] or ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    saved = client.get("/api/items?q=" + top["title"]).json()
    assert saved and saved[0]["status"] == "wishlist"


def test_metadata_search_requires_tmdb_key(logged_in):
    response = logged_in.get("/api/metadata/search?type=movie&q=inception")
    assert response.status_code == 503
    assert "TMDB" in response.json()["detail"]


def test_metadata_search_uses_service(logged_in, monkeypatch):
    from app.schemas.metadata import MetadataResult
    from app.services import metadata_service

    fake = MetadataResult(source="google_books", external_id="abc123", media_type="book", title="Dune", genres=["Fiction"])
    monkeypatch.setattr(metadata_service.google_books_client(), "search", lambda query, limit=10: [fake])
    data = logged_in.get("/api/metadata/search?type=book&q=dune").json()
    assert data["results"][0]["title"] == "Dune"


def test_profile_update_and_account_deletion(logged_in, csrf):
    client = logged_in
    token = csrf("/profile")
    response = client.post(
        "/profile", data={"csrf_token": token, "display_name": "Alice B", "email": "alice@example.com", "bio": "Hi"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert client.get("/api/me").json()["display_name"] == "Alice B"

    wrong = client.post("/profile/delete", data={"csrf_token": token, "delete_password": "nope"})
    assert wrong.status_code == 400
    client.post("/profile/delete", data={"csrf_token": token, "delete_password": "Password123"})
    assert client.get("/dashboard", follow_redirects=False).status_code == 303
