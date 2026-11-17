# Curio

> **Collect what you love. Discover what’s next.**

Curio is a web application for organising your favourite **books, movies, TV shows, songs, albums** and other personal interests in one place. You can rate, tag, annotate and group items into collections, share collections through public links, export them as PDFs, and get **personalised recommendations** from a content-based recommendation engine written in Python.

---

## Contents

1. [Features](#features)
2. [Technology stack](#technology-stack)
3. [Project structure](#project-structure)
4. [Installation and setup](#installation-and-setup)
5. [Environment variables and API credentials](#environment-variables-and-api-credentials)
6. [Database initialisation](#database-initialisation)
7. [Running the application](#running-the-application)
8. [Running the tests](#running-the-tests)
9. [JSON API](#json-api)
10. [Known limitations](#known-limitations)
11. [Verification status](#verification-status)

---

## Features

| Area | What Curio provides |
|------|---------------------|
| **Accounts** | Registration, login and logout; PBKDF2-SHA256 password hashing; session cookies; profile editing (display name, email, bio); password change; account deletion |
| **Library** | Add, view, edit and delete books, movies, TV shows, songs, albums and "other" interests |
| **Personalisation** | 1–5 star ratings, favourites, personal tags, personal notes and a status (Wishlist / In progress / Completed) |
| **Collections** | Create, rename, describe and delete custom collections; add or remove items; an item can belong to many collections |
| **Search and filters** | Full-text search over title, creator, description, notes, genres and tags; filters by type, genre, tag, status, minimum rating and favourites; four sort orders; pagination |
| **Metadata lookup** | Search **TMDB** (movies and TV), **Google Books** (books) and the **iTunes Search API** (songs and albums) from the add-item form to fill in details, genres, keywords and cover art |
| **Recommendations** | Content-based ranking from genres, tags, creators, keywords, ratings and favourites, with a readable reason for every suggestion; starter picks for new users; optional online suggestions; one-click "Add to wishlist" |
| **Dashboard** | Item counts per type, favourites, collections, average rating, rating distribution, top genres, tags, status breakdown, recently added, top rated and suggested items |
| **Sharing** | Public, read-only share links for collections using unguessable tokens; links can be revoked; private notes and tags are never shown publicly |
| **PDF export** | Download one collection, a shared collection or your whole library as a styled PDF generated with ReportLab |
| **Interface** | Responsive Bootstrap 5 layout for desktop and mobile, consistent Curio branding, clear validation messages, empty states and friendly error pages |

## Technology stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5, CSS3, **Bootstrap 5.3**, Bootstrap Icons, vanilla **JavaScript**; Jinja2 server-side templates |
| Backend | **Python** with **FastAPI**, served by Uvicorn |
| Database | **SQLite** |
| ORM | **SQLAlchemy 2.0** (typed `Mapped[...]` models) |
| Validation | Pydantic v2 schemas |
| PDF export | **ReportLab** |
| HTTP client | httpx (for TMDB, Google Books and iTunes) |
| Testing | pytest + FastAPI `TestClient` |
| Version control | Git |

Flask is not used.

## Project structure

```text
Curio/
├── app/
│   ├── main.py                    # FastAPI application factory, middleware, router registration
│   ├── config.py                  # Settings loaded from environment variables / .env
│   ├── database.py                # SQLAlchemy engine, session factory, init_db()
│   ├── core/                      # Cross-cutting concerns
│   │   ├── constants.py           # Media types, statuses, sort options, limits
│   │   ├── security.py            # Password hashing (PBKDF2), secure tokens
│   │   ├── csrf.py                # CSRF token issue/verification
│   │   ├── dependencies.py        # Current-user dependencies, login/logout helpers
│   │   ├── rate_limit.py          # Failed-login throttling
│   │   ├── errors.py              # Domain exceptions + global HTML/JSON error handlers
│   │   ├── forms.py               # Validation error → form message mapping
│   │   └── templating.py          # Jinja2 setup, flash messages, render/redirect helpers
│   ├── models/                    # SQLAlchemy models: User, Item, Tag, Collection + association tables
│   ├── schemas/                   # Pydantic schemas: user, item, collection, metadata, recommendation, stats
│   ├── services/                  # Business logic
│   │   ├── user_service.py        # Registration, authentication, profile, password, deletion
│   │   ├── item_service.py        # Item CRUD, tagging, search, filters, facets
│   │   ├── collection_service.py  # Collection CRUD and membership
│   │   ├── metadata_service.py    # Chooses TMDB / Google Books / iTunes per media type
│   │   ├── recommendation_engine.py   # Pure-Python content-based recommender
│   │   ├── recommendation_service.py  # Builds candidate pool and runs the engine
│   │   ├── stats_service.py       # Dashboard statistics
│   │   ├── sharing_service.py     # Public share tokens
│   │   ├── pdf_export.py          # ReportLab PDF generation
│   │   ├── text_utils.py          # Genre normalisation, keyword extraction
│   │   └── demo_data.py           # Optional demo account
│   ├── clients/                   # External API clients (base, tmdb, google_books, itunes)
│   ├── routers/                   # HTTP routes (pages + /api JSON endpoints)
│   ├── data/catalogue.json        # Bundled starter catalogue used for recommendations
│   ├── templates/                 # Jinja2 HTML templates (base layout, pages, partials)
│   └── static/                    # curio.css, curio.js, lookup.js, favicon
├── scripts/init_db.py             # Creates tables; --demo seeds a demo account
├── tests/                         # pytest unit and integration tests
├── docs/PROJECT_DOCUMENTATION.md  # Detailed project documentation
├── DELIVERABLES.md                # File-by-file list of deliverables
├── requirements.txt               # Runtime dependencies
├── requirements-dev.txt           # Runtime + test dependencies
├── .env.example                   # Template for environment variables (no secrets)
└── .gitignore
```

## Installation and setup

**Prerequisites:** Python **3.10 or newer** (the test run used 3.14), `pip`, and an internet connection for installing packages and calling the metadata APIs.

Run these commands from the project folder.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then open `.env` and fill in the values described below. At minimum, set `CURIO_SECRET_KEY`.

## Environment variables and API credentials

All configuration comes from environment variables, which are normally kept in a local `.env` file. `.env` is excluded from Git; `.env.example` is the template and contains no secrets.

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `CURIO_SECRET_KEY` | Recommended | random per start-up | Signs session cookies. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. If empty, everyone is logged out whenever the server restarts. |
| `CURIO_DATABASE_URL` | No | `sqlite:///<project>/data/curio.db` | SQLAlchemy database URL |
| `CURIO_ENV` | No | `development` | Environment label |
| `CURIO_DEBUG` | No | `false` | FastAPI debug mode (development only) |
| `CURIO_SESSION_MAX_AGE` | No | `1209600` (14 days) | Session lifetime in seconds |
| `CURIO_SECURE_COOKIES` | No | `false` | Set to `true` when served over HTTPS |
| `CURIO_HTTP_TIMEOUT` | No | `8` | Timeout (seconds) for external API calls |
| `TMDB_READ_ACCESS_TOKEN` | For movie/TV lookup | – | TMDB v4 read access token (preferred) |
| `TMDB_API_KEY` | For movie/TV lookup | – | TMDB v3 API key (alternative to the token) |
| `GOOGLE_BOOKS_API_KEY` | No | – | Optional; without it Google Books uses a small shared quota |
| `ITUNES_COUNTRY` | No | `US` | Two-letter iTunes store country |

### Getting the API credentials

* **TMDB (movies and TV):** create a free account at <https://www.themoviedb.org/>, open *Settings → API*, request an API key, then copy the **API Read Access Token** into `TMDB_READ_ACCESS_TOKEN` (or the v3 key into `TMDB_API_KEY`). Without TMDB credentials, movie and TV lookup shows a clear "needs a TMDB key" message and you can still enter details by hand.
* **Google Books (books):** works without a key. For a personal quota, create an API key in the Google Cloud Console, enable the *Books API*, and set `GOOGLE_BOOKS_API_KEY`.
* **iTunes Search API (songs and albums):** no key is needed.

API keys are only ever used on the server. The browser calls Curio's own `/api/metadata/*` endpoints, so keys are never exposed to the browser.

## Database initialisation

Tables are created automatically when the application starts. You can also create them explicitly:

```bash
python -m scripts.init_db
```

To create a **demo account** with sample items, ratings, tags and two collections (one of them shared) for presentations:

```bash
python -m scripts.init_db --demo
```

Demo login: username **`demo`**, password **`CurioDemo123`**. Use the demo account only locally; do not create it on a public deployment.

The database is a single SQLite file at `data/curio.db`. To start again from scratch, stop the server and delete that file.

## Running the application

With the virtual environment activated:

```bash
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000> in a browser.

* `--reload` restarts the server when code changes (development only).
* Interactive API documentation is available at <http://127.0.0.1:8000/api/docs>.
* A health check is available at <http://127.0.0.1:8000/health>.

## Running the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests use a temporary SQLite database and never call the real external APIs (metadata calls are stubbed).

## JSON API

Every page is server-rendered, but the main data is also available as JSON for the signed-in user. The full list is in `/api/docs`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/me` | Current user profile |
| GET | `/api/items` | List or search items (`q`, `type`, `tag`, `genre`, `favourites`, `sort`, `page`) |
| GET | `/api/items/{id}` | One item |
| POST | `/api/items/{id}/favourite` | Toggle favourite (requires the `X-CSRF-Token` header) |
| GET | `/api/collections` | List collections |
| GET | `/api/metadata/sources` | Which metadata providers are configured |
| GET | `/api/metadata/search?type=&q=` | Search TMDB / Google Books / iTunes |
| GET | `/api/metadata/details?type=&source=&id=` | Full details for one result |
| GET | `/api/recommendations` | Ranked recommendations (`type`, `online`, `limit`) |
| GET | `/api/stats` | Dashboard statistics |

## Known limitations

* **No database migrations.** Tables are created with `create_all()`. If the models change, an existing database must be recreated (or Alembic added).
* **Single-process assumptions.** The failed-login limiter and the metadata cache live in memory. They reset on restart and are not shared between multiple server workers.
* **PDF fonts.** PDFs use the built-in Helvetica font, which covers Western European characters only; titles in other scripts (for example Chinese or Arabic) will not render correctly. Cover images are not embedded in PDFs.
* **External services.** TMDB needs your own free API key. Google Books without a key has a small shared daily quota. The iTunes API has no "popular by genre" endpoint, so online music suggestions are based on a genre search term. Cover images are loaded directly from the providers' servers.
* **Recommendation catalogue.** The bundled starter catalogue is intentionally small (65 well-known titles). Wider suggestions come from the community (other users' shared collections) and from the optional online mode.
* **Accounts.** There is no email verification, password-reset email or administrator role.
* **Sessions.** Session data (user id and CSRF token only) is stored in a signed cookie, so it cannot be tampered with, but it is not encrypted.
* **Deployment.** The hosting platform and production configuration (HTTPS termination, process manager, backups) are **to be decided**. Curio is set up for local use; see `docs/PROJECT_DOCUMENTATION.md`.
* **Licence:** **To be decided.** Choose a licence (for example MIT) if the code will be published.

## Verification status

* The automated test suite (28 tests covering authentication, CSRF, items, search and filters, collections, sharing, PDF export, statistics, recommendations and the metadata endpoints) passed in an isolated virtual environment with Python 3.14, FastAPI 0.163, SQLAlchemy 2.0.58, Pydantic 2.14 and ReportLab 5.1.
* A smoke test using the demo account loaded every main page and PDF export successfully through FastAPI's test client.
* The **live** TMDB, Google Books and iTunes APIs were **not** called during verification (no credentials were available, and the tests stub these calls). Check the lookup feature with your own keys before a demonstration.
