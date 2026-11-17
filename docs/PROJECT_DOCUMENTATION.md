# Curio — Project Documentation

**Curio** · *Collect what you love. Discover what’s next.*

A personal interest collections management platform built with FastAPI, SQLite, SQLAlchemy, Bootstrap and ReportLab.

---

## 1. Project objectives

1. **Centralise personal interests.** Give users a single place to record the books, movies, TV shows, songs, albums and other interests they love, instead of spreading them across several apps.
2. **Support rich personal organisation.** Let users rate, favourite, tag, annotate and group items into custom collections, then find them again quickly through search and filters.
3. **Reduce data-entry effort.** Fill in titles, creators, years, descriptions, genres and artwork automatically from public metadata services (TMDB, Google Books and iTunes).
4. **Help users discover new items.** Recommend new titles with a transparent, content-based recommendation engine that runs locally in Python and needs no paid AI service.
5. **Enable sharing and portability.** Let users share collections with a public link and export collections or the whole library as PDF documents.
6. **Provide a professional user experience.** Deliver a consistent, responsive and accessible interface branded as Curio.

### Scope

In scope: a single web application with user accounts, personal libraries, collections, metadata lookup, recommendations, dashboard statistics, public sharing and PDF export.

Out of scope for this version: native mobile apps, social features (following, comments), email notifications, administrator tools and production hosting (see §9).

---

## 2. Functional requirements

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-1 | A visitor can register with a username, email and password. | `routers/auth.py`, `services/user_service.register_user`, `schemas/user.UserCreate` |
| FR-2 | A registered user can log in with their username or email and log out. | `routers/auth.py`, `core/dependencies.login_user / logout_user` |
| FR-3 | Passwords are stored only as salted hashes. | `core/security.py` (PBKDF2-HMAC-SHA256) |
| FR-4 | A user can view and edit their profile (display name, email, bio), change their password and delete their account. | `routers/profile.py`, `services/user_service.py` |
| FR-5 | A user can add, view, edit and delete items of type book, movie, TV show, song, album or other. | `routers/items.py`, `services/item_service.py` |
| FR-6 | A user can rate an item (1–5), mark it as a favourite, add tags and write personal notes. | `models/item.py`, `models/tag.py`, item form template |
| FR-7 | A user can track an item's status: Wishlist, In progress or Completed. | `Item.status`, `core/constants.STATUSES` |
| FR-8 | A user can create, rename, describe and delete collections. | `routers/collections.py`, `services/collection_service.py` |
| FR-9 | A user can add items to collections and remove them; an item may belong to several collections. | `collection_items` association table; collection detail page; item form and item detail page |
| FR-10 | A user can search their library and filter it by type, genre, tag, status, minimum rating and favourites, sort the results and page through them. | `services/item_service.ItemFilters`, `list_items` |
| FR-11 | A user can look up item details online: movies/TV via TMDB, books via Google Books, songs/albums via iTunes. | `clients/*`, `services/metadata_service.py`, `routers/metadata.py`, `static/js/lookup.js` |
| FR-12 | The system recommends items using the user's genres, tags, keywords, creators, ratings and favourites, and explains each recommendation. | `services/recommendation_engine.py`, `services/recommendation_service.py` |
| FR-13 | A user can save a recommendation to their library as a wishlist item. | `POST /recommendations/save` |
| FR-14 | A dashboard shows collection counts and personal statistics. | `services/stats_service.py`, `templates/dashboard.html` |
| FR-15 | A user can create, copy and revoke a public read-only link for a collection. | `services/sharing_service.py`, `routers/sharing.py` |
| FR-16 | Anyone with a valid share link can view the shared collection and download it as a PDF without logging in. | `GET /shared/{token}`, `GET /shared/{token}/export.pdf` |
| FR-17 | A user can export a collection or the whole library to PDF. | `services/pdf_export.py`, `routers/export.py` |
| FR-18 | Invalid input produces clear, field-level validation messages. | Pydantic schemas + `core/forms.validation_errors` |

## 3. Non-functional requirements

| ID | Category | Requirement and how it is met |
|----|----------|-------------------------------|
| NFR-1 | Usability | A consistent Bootstrap 5 theme, clear navigation, empty states, inline validation messages, confirmation prompts for destructive actions and toast feedback for asynchronous actions. |
| NFR-2 | Responsiveness | Layouts use the Bootstrap grid and CSS grid with mobile breakpoints; the navigation collapses on small screens; the item grid becomes two columns on phones. |
| NFR-3 | Accessibility | Semantic headings and landmarks, a skip link, `aria-label`s on icon buttons, visible focus states, `role="status"` live regions and a `prefers-reduced-motion` override. |
| NFR-4 | Security | Hashed passwords, CSRF protection, signed session cookies, ownership checks on every query, unguessable share tokens, login throttling and security headers (see §7). |
| NFR-5 | Maintainability | Layered architecture (routers → services → models), typed SQLAlchemy 2.0 models, Pydantic schemas, small focused modules and an automated test suite. |
| NFR-6 | Configurability | All secrets and settings are read from environment variables; `.env.example` documents every variable. |
| NFR-7 | Resilience | External API failures, time-outs, rate limits and missing credentials are caught and shown as friendly messages; the rest of the application keeps working. |
| NFR-8 | Performance | Indexed foreign keys and lookups, paginated lists, `selectinload` to avoid N+1 queries, and in-memory caching of metadata responses (30 minutes). |
| NFR-9 | Portability | SQLite needs no database server; the project runs on Windows, macOS and Linux with Python 3.10+. |
| NFR-10 | Cost | No paid services are required. Recommendations run locally; Google Books and iTunes work without keys; TMDB keys are free. |

---

## 4. Architecture and application modules

Curio uses a **layered, server-rendered architecture**:

1. **Presentation layer:** Jinja2 templates styled with Bootstrap and `curio.css`, plus small vanilla-JavaScript enhancements (`curio.js`, `lookup.js`).
2. **Routing layer (`app/routers`):** thin FastAPI route functions that parse input, call services and render templates or return JSON.
3. **Service layer (`app/services`):** all business rules: validation beyond schemas, ownership checks, recommendations, statistics, sharing and PDF generation.
4. **Integration layer (`app/clients`):** HTTP clients for the external metadata providers.
5. **Data layer (`app/models`, `app/database.py`):** SQLAlchemy ORM models on SQLite.

Cross-cutting concerns (configuration, security, CSRF, error handling, templating) live in `app/core`.

### Modules

| Module | Responsibility |
|--------|----------------|
| `app/main.py` | Application factory: session middleware, security headers, static files, routers, exception handlers, start-up table creation |
| `app/config.py` | Typed, immutable settings from environment variables; paths; branding constants |
| `app/database.py` | Engine creation (SQLite foreign keys enabled), session factory, `get_db` dependency, `init_db` |
| `app/core/security.py` | PBKDF2 password hashing and verification, rehash detection, secure tokens |
| `app/core/csrf.py` | Per-session CSRF token; verification from a form field or the `X-CSRF-Token` header |
| `app/core/dependencies.py` | `get_current_user`, `get_current_user_optional`, session login/logout |
| `app/core/rate_limit.py` | Sliding-window limiter for failed logins |
| `app/core/errors.py` | Domain exceptions (`NotFoundError`, `ConflictError`, …) and global handlers that return HTML pages or JSON |
| `app/core/templating.py` | Jinja2 environment, globals and filters, flash messages, `render`, safe redirects |
| **Authentication and profile** — `routers/auth.py`, `routers/profile.py`, `services/user_service.py` | Registration, login and logout, profile updates, password change, account deletion |
| **Item management** — `routers/items.py`, `services/item_service.py` | CRUD, tagging, keyword extraction, search, filters, sorting, pagination, facets |
| **Collection management** — `routers/collections.py`, `services/collection_service.py` | CRUD, membership, unique names per user |
| **External metadata** — `clients/*`, `services/metadata_service.py`, `routers/metadata.py` | Provider selection, normalisation into `MetadataResult`, error mapping, caching |
| **Recommendations** — `services/recommendation_engine.py`, `services/recommendation_service.py`, `routers/recommendations.py` | Candidate pool, scoring, explanations, cold start, saving suggestions |
| **Dashboard** — `services/stats_service.py`, `routers/dashboard.py` | Aggregated statistics and the dashboard page |
| **Sharing** — `services/sharing_service.py`, `routers/sharing.py` | Share tokens and the public read-only page |
| **PDF export** — `services/pdf_export.py`, `routers/export.py` | ReportLab document generation and downloads |
| **Text utilities** — `services/text_utils.py` | Genre canonicalisation, list cleaning, keyword extraction |

---

## 5. Database entities and relationships

The database is SQLite, accessed through SQLAlchemy 2.0. Foreign keys are enforced with `PRAGMA foreign_keys=ON`, and deletes cascade at both the ORM and database level.

### 5.1 Entities

**`users`**

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| username | VARCHAR(30) | unique, indexed; case-insensitive uniqueness enforced in the service |
| email | VARCHAR(255) | unique, indexed, stored lower-case |
| password_hash | VARCHAR(255) | `pbkdf2_sha256$iterations$salt$hash` |
| display_name | VARCHAR(80) | optional |
| bio | TEXT | optional |
| created_at, updated_at | DATETIME | UTC |

**`items`**

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | FK → users.id | `ON DELETE CASCADE`, indexed |
| media_type | VARCHAR(20) | book, movie, tv, song, album, other; composite index with user_id |
| title | VARCHAR(255) | required |
| creator | VARCHAR(255) | author, director, show creator or artist |
| release_year | INTEGER | 1000–2100 |
| description | TEXT | |
| genres | VARCHAR(500) | comma-separated canonical genres (e.g. `Science Fiction,Drama`) |
| keywords | VARCHAR(1000) | comma-separated keywords (from TMDB plus extracted terms) |
| image_url | VARCHAR(1000) | cover or poster URL (HTTPS) |
| external_source | VARCHAR(30) | manual, tmdb, google_books, itunes, catalogue, community |
| external_id / external_url | VARCHAR | provider id and link |
| rating | INTEGER | nullable; `CHECK rating BETWEEN 1 AND 5` |
| is_favourite | BOOLEAN | |
| status | VARCHAR(20) | wishlist, in_progress, completed |
| notes | TEXT | private personal notes |
| created_at, updated_at | DATETIME | |

**`tags`**: `id`, `user_id` (FK → users, cascade) and `name` (VARCHAR(40), lower-case), with a unique constraint on (`user_id`, `name`). Tags are private to each user.

**`collections`**: `id`, `user_id` (FK → users, cascade), `name` (VARCHAR(100), unique per user), `description`, `share_token` (VARCHAR(64), unique, nullable; non-null means publicly shared), `shared_at`, `created_at` and `updated_at`.

**Association tables**

* **`item_tags`** (`item_id` FK, `tag_id` FK; composite PK; both cascade): many-to-many between items and tags.
* **`collection_items`** (`collection_id` FK, `item_id` FK, `added_at`; composite PK; both cascade): many-to-many between collections and items.

### 5.2 Relationships

| Relationship | Cardinality | Behaviour |
|--------------|-------------|-----------|
| User → Item | one-to-many | deleting a user deletes their items |
| User → Collection | one-to-many | deleting a user deletes their collections |
| User → Tag | one-to-many | deleting a user deletes their tags |
| Item ↔ Tag | many-to-many via `item_tags` | unused tags are pruned after edits and deletions |
| Collection ↔ Item | many-to-many via `collection_items` | deleting a collection keeps its items in the library; deleting an item removes it from all collections |

Every service query filters by `user_id`, so a user can never read or change another user's data. The only exception is the public share page, which is reached through an unguessable token.

---

## 6. Recommendation approach

Curio uses a **content-based recommender** (`app/services/recommendation_engine.py`), written in plain Python without external machine-learning libraries or paid AI APIs.

### 6.1 Candidate pool

| Source | Description |
|--------|-------------|
| Curio catalogue | `app/data/catalogue.json`: 65 well-known books, films, TV shows, songs and albums with genres, creators and keywords. Always available, offline and without API keys. |
| Community | Items in collections that **other** users have shared publicly. |
| Online (optional) | When the user ticks "Include online suggestions": genre-based discovery from TMDB (`/discover`), Google Books (`subject:` search) and iTunes (genre search term), using the user's two strongest genres in each of their three strongest media types. |

Candidates that match something the user already owns (same provider id, or same media type and normalised title) are removed, and duplicates within the pool are merged.

### 6.2 Feature extraction

Each item becomes a sparse vector of weighted features:

| Feature | Example | Weight |
|---------|---------|--------|
| `genre:<name>` | `genre:science fiction` | 1.00 |
| `tag:<name>` | `tag:rewatch` | 0.80 |
| `creator:<name>` | `creator:christopher nolan` | 0.70 |
| `keyword:<term>` | `keyword:space` | 0.45 |
| `type:<media type>` | `type:movie` | 0.25 |

Genres are **canonicalised** so that different providers' labels match. For example, "Sci-Fi" becomes "science fiction", TMDB's "Sci-Fi & Fantasy" becomes "science fiction" and "fantasy", and Google Books' "Fiction / Science Fiction / General" becomes "fiction" and "science fiction". Keywords come from TMDB keyword lists and from a simple frequency-based extractor (stop words removed) applied to titles and descriptions.

### 6.3 User profile

The profile `P` is the weighted sum of the vectors of the user's items:

```
P = Σ_items  w(item) · v(item)

w(item) = 1.0                  if unrated
        = (rating − 2.5) × 0.8 if rated   → 1★ −1.2, 2★ −0.4, 3★ +0.4, 4★ +1.2, 5★ +2.0
        + 1.5                  if the item is a favourite
```

Low ratings produce **negative** weights, so traits of disliked items push similar candidates down.

### 6.4 IDF weighting and scoring

Features that occur on nearly every item (for example "Drama") carry little information, so each feature `f` is scaled by its inverse document frequency over the library and the candidate pool:

```
idf(f) = ln((1 + N) / (1 + df(f))) + 1
```

Each candidate `c` is scored with **cosine similarity** in the IDF-weighted space:

```
score(c) = Σ_f (P_f·idf_f)(c_f·idf_f) / ( ‖P·idf‖ · ‖c·idf‖ )
```

A candidate is kept only if its score is positive **and** it matches the profile on at least one meaningful feature (genre, tag, creator or keyword; a matching media type alone is not enough). Results are sorted by score. The displayed "match %" is relative: the strongest suggestion shows 95% and the others are scaled against it.

### 6.5 Explanations

The features that contributed most to a candidate's score are turned into reasons, for example:

* *Matches your taste for Science Fiction and Drama*
* *More from Denis Villeneuve*
* *Similar to things you tagged “rewatch”*
* *Shares themes like “space” and “astronaut”*

The recommendations page also shows the user's **taste profile**: their strongest positive genres, creators and tags.

### 6.6 Cold start

When a user has fewer than three items and no profile can be built, Curio shows **starter picks**: catalogue entries marked as starters, two or three per media type. The page explains that adding and rating items will unlock personalised suggestions.

### 6.7 Why content-based?

Collaborative filtering needs many users with overlapping ratings, which a new, small application will not have. A content-based approach works from the first few saved items, is explainable, runs offline, and is easy to unit-test (see `tests/test_recommendation_engine.py`).

---

## 7. External API integrations

All provider calls are made **server-side** through `app/clients/*`, so API keys never reach the browser. The browser calls Curio's `/api/metadata/search` and `/api/metadata/details`, and both require a logged-in user.

| Provider | Media types | Endpoints used | Authentication | Data mapped |
|----------|-------------|----------------|----------------|-------------|
| **TMDB** | movie, tv | `/search/{movie,tv}`, `/{movie,tv}/{id}?append_to_response=credits,keywords`, `/genre/{movie,tv}/list`, `/discover/{movie,tv}` | `TMDB_READ_ACCESS_TOKEN` (Bearer) or `TMDB_API_KEY` | title, year, overview, genres, director or creator, keywords, poster (`image.tmdb.org/t/p/w500`), TMDB page link |
| **Google Books** | book | `/books/v1/volumes?q=…`, `/books/v1/volumes/{id}` | optional `GOOGLE_BOOKS_API_KEY` | title, authors, published year, description (HTML stripped), categories, thumbnail (forced to HTTPS), info link |
| **iTunes Search** | song, album | `/search?media=music&entity=song|album`, `/lookup?id=` | none | track or album name, artist, release year, primary genre, artwork upscaled to 600×600, store link |

**Shared behaviour** (`clients/base.py`):

* A configurable timeout (`CURIO_HTTP_TIMEOUT`, default 8 s) and a generic `User-Agent` that contains no personal data.
* Errors are mapped to friendly messages: time-outs, network failures, 401/403 (bad credentials), 404, 429 (rate limit) and other HTTP errors. The service layer converts them into HTTP 502 or 503 JSON responses.
* An in-memory cache keeps responses, including TMDB genre lists, for 30 minutes. Credentials are never part of cache keys.
* Identifiers are validated with strict patterns before they are placed in a URL path, which prevents path injection.
* If TMDB is not configured, the add-item form explains how to add the key and lets the user enter details by hand.

---

## 8. Security measures

| Threat | Mitigation |
|--------|------------|
| Password theft from the database | PBKDF2-HMAC-SHA256 with 600,000 iterations and a 16-byte random salt per password (standard library). Hashes record their iteration count and are transparently upgraded on login if the work factor increases. |
| User enumeration through timing | Failed logins for unknown usernames still run a dummy hash verification; the error message does not reveal which part was wrong. |
| Brute-force login | At most 5 failed attempts per client IP and identifier in 10 minutes (HTTP 429). |
| Session tampering or fixation | Sessions are signed with `itsdangerous` using `CURIO_SECRET_KEY`. Cookies are `HttpOnly` and `SameSite=Lax`, and `Secure` when `CURIO_SECURE_COOKIES=true`. The session is cleared and the CSRF token rotated on every login and logout. |
| Cross-site request forgery | Every state-changing request needs a per-session CSRF token, either a hidden form field or the `X-CSRF-Token` header for `fetch` calls, compared in constant time. |
| Unauthorised data access (IDOR) | Every item and collection lookup checks `user_id`; other users' records return 404. |
| Open redirects | The `next` parameter after login only accepts local paths. |
| Cross-site scripting | Jinja2 auto-escaping for all template output; JavaScript builds lookup results with `textContent`; PDF text is XML-escaped before ReportLab renders it. |
| SQL injection | All queries go through SQLAlchemy with bound parameters; `LIKE` wildcards in search terms are escaped. |
| Share-link guessing | Share tokens come from `secrets.token_urlsafe(18)` (~144 bits). Disabling sharing deletes the token, which revokes the link immediately. Shared pages carry `noindex` headers. |
| Privacy of personal data | Public pages and public PDFs never include notes, tags or the owner's email address. |
| Clickjacking and content sniffing | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` and `Permissions-Policy` headers. |
| Secret leakage | Secrets are only read from environment variables. `.env` is git-ignored, `.env.example` contains no secrets, and API keys stay on the server. |
| Input abuse | Pydantic schemas enforce types, lengths and ranges (e.g. rating 1–5, year 1000–2100, URL format), and the database adds a CHECK constraint on rating. |

---

## 9. Setup assumptions and limitations

### Assumptions

* Python 3.10 or newer is installed (the test run used Python 3.14).
* The application runs locally, for example for a demonstration or evaluation, with one Uvicorn process.
* An internet connection is available for the CDN-hosted Bootstrap and fonts and for the metadata APIs. Without it the layout falls back to system fonts and unstyled Bootstrap components, and lookups fail with a friendly message.
* The user creates their own TMDB credentials. Google Books and iTunes work without credentials.

### Limitations

* No schema migrations (Alembic is not included); a model change requires recreating `data/curio.db`.
* The login limiter and API cache are stored in memory, per process.
* PDFs use the built-in Helvetica font: non-Latin scripts are not supported and cover images are not embedded.
* Online music suggestions use iTunes genre search terms, because there is no popularity-by-genre endpoint.
* The bundled catalogue is small (65 titles).
* There is no email verification, password reset by email or administrator interface.
* Cover images are loaded directly from third-party servers.

### To be decided

* **Production hosting and deployment:** the target platform, HTTPS termination, process manager and backup strategy need a decision from the project owner. Once decided, set `CURIO_SECURE_COOKIES=true`, provide a strong `CURIO_SECRET_KEY`, and consider moving from SQLite to PostgreSQL by changing `CURIO_DATABASE_URL`.
* **Licence:** choose a licence if the source code will be published.

---

## 10. Testing

`tests/` contains 28 pytest tests:

* `test_security_and_text.py`: password hashing, genre canonicalisation, list cleaning and keyword extraction.
* `test_recommendation_engine.py`: ranking order, exclusion of owned items, negative ratings, media-type filtering, profile requirements and cold-start picks.
* `test_app_flows.py`: end-to-end flows through FastAPI's `TestClient`, covering the landing page and branding, the authentication redirect, CSRF rejection, registration validation, the login and logout cycle, item create, edit, search, filter, favourite and delete, form validation, collections, sharing and the public view, PDF exports, statistics, recommendations and saving them, metadata endpoints with a stubbed provider, and profile update and deletion.

Run them with `python -m pytest` after installing `requirements-dev.txt`. The external providers are never called live in tests.
