"""Shared pytest fixtures.

The test database is a temporary SQLite file, configured through environment
variables *before* the application modules are imported.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="curio-tests-"))
os.environ["CURIO_DATABASE_URL"] = f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}"
os.environ["CURIO_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["TMDB_API_KEY"] = ""
os.environ["TMDB_READ_ACCESS_TOKEN"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

CSRF_RE = re.compile(r'name="csrf-token" content="([^"]+)"')


def extract_csrf(html: str) -> str:
    match = CSRF_RE.search(html)
    assert match, "CSRF token not found in page"
    return match.group(1)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def csrf(client):
    """Return a function that fetches a fresh CSRF token for the client's session."""

    def _get(path: str = "/login") -> str:
        response = client.get(path)
        return extract_csrf(response.text)

    return _get


@pytest.fixture()
def logged_in(client, csrf):
    """Register and sign in a user; returns the client."""
    token = csrf("/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "username": "alice",
            "email": "alice@example.com",
            "display_name": "Alice",
            "password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return client
