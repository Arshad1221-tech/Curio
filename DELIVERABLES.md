# Curio — Deliverables

**Curio** · *Collect what you love. Discover what’s next.*

This document lists every file in the submission and what it does, followed by the implementation status of each requested feature.

## 1. Feature checklist

| Feature | Status | Where |
|---------|--------|-------|
| User registration, login and logout | Implemented | `app/routers/auth.py`, `app/services/user_service.py` |
| Secure password hashing | Implemented (PBKDF2-SHA256, 600k iterations, per-user salt) | `app/core/security.py` |
| User profile management (details, password, account deletion) | Implemented | `app/routers/profile.py`, `app/templates/profile/profile.html` |
| Add, view, edit and delete books, movies, TV shows, songs (+ albums, other) | Implemented | `app/routers/items.py`, `app/services/item_service.py` |
| Create, rename and delete custom collections | Implemented | `app/routers/collections.py`, `app/services/collection_service.py` |
| Organise items into collections and lists (status lists: Wishlist / In progress / Completed) | Implemented | `collection_items` table, `Item.status` |
| Ratings, favourites, tags and personal notes | Implemented | `app/models/item.py`, `app/models/tag.py` |
| Search and filter items | Implemented (text search; type, genre, tag, status, rating and favourite filters; sorting; pagination) | `app/services/item_service.py`, `app/templates/items/list.html` |
| TMDB movie/TV metadata and posters | Implemented; **requires your free TMDB key** in `.env` | `app/clients/tmdb.py` |
| Google Books book information and covers | Implemented (key optional) | `app/clients/google_books.py` |
| iTunes song and album information and artwork | Implemented (no key needed) | `app/clients/itunes.py` |
| API credentials in environment variables + `.env.example` | Implemented | `app/config.py`, `.env.example` |
| Content-based recommendations (genres, tags, keywords, ratings, favourites) | Implemented in pure Python, with explanations and cold start | `app/services/recommendation_engine.py`, `app/services/recommendation_service.py` |
| Dashboard with counts and personal statistics | Implemented | `app/services/stats_service.py`, `app/templates/dashboard.html` |
| Public sharing links for collections | Implemented (create, copy, revoke; read-only public page) | `app/services/sharing_service.py`, `app/routers/sharing.py` |
| Export collections to PDF (ReportLab) | Implemented (collection, shared collection, whole library) | `app/services/pdf_export.py`, `app/routers/export.py` |
| Responsive interface for desktop and mobile | Implemented with Bootstrap 5 | `app/templates/`, `app/static/css/curio.css` |
| Curio name and tagline on the landing page and README | Implemented | `app/templates/landing.html`, `README.md` |
| Error handling and input validation | Implemented (HTML error pages, JSON errors for `/api`, field-level form errors) | `app/core/errors.py`, `app/core/forms.py`, `app/schemas/` |
| Automated tests | 28 tests, all passing in the verification environment (see README) | `tests/` |

## 2. Files and their purposes

### Root

| File | Purpose |
|------|---------|
| `README.md` | Overview, features, stack, structure, setup, environment variables, database initialisation, running, tests, API, limitations |
| `DELIVERABLES.md` | This file: deliverables and feature status |
| `docs/PROJECT_DOCUMENTATION.md` | Objectives, requirements, modules, database design, recommendation approach, API integrations, security, assumptions and limitations |
| `requirements.txt` | Runtime dependencies (FastAPI, Uvicorn, SQLAlchemy, Pydantic, Jinja2, python-multipart, itsdangerous, httpx, ReportLab, python-dotenv) |
| `requirements-dev.txt` | Runtime dependencies plus pytest |
| `.env.example` | Template for all environment variables; contains no secrets |
| `.gitignore` | Excludes virtual environments, `.env`, the SQLite database, caches and archives |

### Application core (`app/`)

| File | Purpose |
|------|---------|
| `app/__init__.py` | Package marker and version |
| `app/main.py` | FastAPI application factory: middleware, security headers, static files, routers, error handlers, start-up DB creation |
| `app/config.py` | Environment-driven settings, paths, app name and tagline |
| `app/database.py` | SQLAlchemy engine (SQLite foreign keys on), session factory, `get_db`, `init_db` |
| `app/core/constants.py` | Media types, statuses, sources, sort options and limits |
| `app/core/security.py` | Password hashing and verification, rehash detection, secure tokens |
| `app/core/csrf.py` | CSRF token generation and verification |
| `app/core/dependencies.py` | Current-user dependencies, login and logout session handling |
| `app/core/rate_limit.py` | Failed-login throttling |
| `app/core/errors.py` | Domain exceptions and global exception handlers |
| `app/core/forms.py` | Converts validation errors into form messages |
| `app/core/templating.py` | Jinja2 configuration, flash messages, render/redirect helpers, safe `next` URLs |

### Models (`app/models/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Exports all models |
| `base.py` | UTC timestamp helper |
| `associations.py` | `item_tags` and `collection_items` many-to-many tables |
| `user.py` | `User` model |
| `item.py` | `Item` model with rating constraint and helper properties |
| `tag.py` | `Tag` model (unique per user) |
| `collection.py` | `Collection` model with share token |

### Schemas (`app/schemas/`)

| File | Purpose |
|------|---------|
| `user.py` | Registration, profile update, password change, user output |
| `item.py` | Item input validation (genres, tags, URLs, ranges) and output |
| `collection.py` | Collection input and output |
| `metadata.py` | Normalised external metadata result and source status |
| `recommendation.py` | Recommendation JSON output |
| `stats.py` | Dashboard statistics JSON output |

### Services (`app/services/`)

| File | Purpose |
|------|---------|
| `user_service.py` | Registration, authentication, profile, password, deletion, account summary |
| `item_service.py` | Item CRUD, tags, keywords, search, filters, sorting, pagination, facets |
| `collection_service.py` | Collection CRUD and membership |
| `metadata_service.py` | Chooses the right provider and converts errors |
| `recommendation_engine.py` | Pure-Python content-based recommender (features, profile, IDF, cosine, explanations) |
| `recommendation_service.py` | Builds catalogue, community and online candidates and runs the engine |
| `stats_service.py` | Dashboard statistics |
| `sharing_service.py` | Share tokens and public lookup |
| `pdf_export.py` | ReportLab PDF generation |
| `text_utils.py` | Genre canonicalisation, list cleaning, keyword extraction |
| `demo_data.py` | Optional demo account for presentations |

### External API clients (`app/clients/`)

| File | Purpose |
|------|---------|
| `base.py` | Shared HTTP helper, error mapping, TTL cache, year/HTTPS helpers |
| `tmdb.py` | TMDB search, details (credits, keywords), genres, discover |
| `google_books.py` | Google Books search, details, subject discovery |
| `itunes.py` | iTunes song/album search, lookup, genre search |

### Routes (`app/routers/`)

| File | Purpose |
|------|---------|
| `pages.py` | Landing page |
| `auth.py` | Register, login, logout |
| `profile.py` | Profile page, updates, password, deletion, `/api/me` |
| `dashboard.py` | Dashboard page, `/api/stats` |
| `items.py` | Library, item forms, detail, delete, collections, `/api/items` |
| `collections.py` | Collections list, detail, edit, delete, membership, `/api/collections` |
| `metadata.py` | `/api/metadata/sources`, `/search`, `/details` |
| `recommendations.py` | Discover page, save suggestion, `/api/recommendations` |
| `sharing.py` | Enable/disable sharing, public page and public PDF |
| `export.py` | Collection and library PDF downloads |

### Data, templates and static files

| File | Purpose |
|------|---------|
| `app/data/catalogue.json` | Starter catalogue of 65 titles for recommendations |
| `app/templates/base.html` | Shared layout: navigation, flash messages, footer, assets |
| `app/templates/landing.html` | Branded landing page with name and tagline |
| `app/templates/dashboard.html` | Statistics dashboard |
| `app/templates/auth/login.html`, `register.html` | Authentication forms |
| `app/templates/profile/profile.html` | Profile, password and account deletion |
| `app/templates/items/list.html`, `form.html`, `detail.html` | Library, add/edit form with online lookup, item details |
| `app/templates/collections/list.html`, `detail.html` | Collections overview and detail with sharing panel |
| `app/templates/recommendations/index.html` | Discover page |
| `app/templates/shared/collection.html` | Public shared collection page |
| `app/templates/errors/error.html` | Friendly error page |
| `app/templates/partials/_macros.html` | Reusable UI macros (covers, stars, errors, empty states, pagination) |
| `app/templates/partials/_item_card.html`, `_recommendation_card.html`, `_logo.html` | Card components and logo |
| `app/static/css/curio.css` | Curio theme (palette, typography, components, responsive rules) |
| `app/static/js/curio.js` | Favourite toggles, toasts, confirmations, copy link, filters, image preview |
| `app/static/js/lookup.js` | "Find it online" metadata lookup on the item form |
| `app/static/img/favicon.svg` | Curio icon |

### Scripts and tests

| File | Purpose |
|------|---------|
| `scripts/init_db.py` | Creates tables; `--demo` adds a demo account |
| `tests/conftest.py` | Test configuration with a temporary database and fixtures |
| `tests/test_security_and_text.py` | Hashing and text-utility unit tests |
| `tests/test_recommendation_engine.py` | Recommendation engine unit tests |
| `tests/test_app_flows.py` | End-to-end application flow tests |

## 3. Submission archive

`personal-interest-collections-platform.zip`, in the project root, contains all of the files listed above. It excludes `.git`, `.env` and other secrets, the SQLite database, virtual environments and caches. The archive itself is git-ignored.

## 4. Items requiring your input

* **TMDB credentials:** add your own key to `.env` to enable movie and TV lookup (see README).
* **Hosting and deployment:** to be decided (see `docs/PROJECT_DOCUMENTATION.md` §9).
* **Licence:** to be decided.
