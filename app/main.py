"""FastAPI application entry point for Curio.

Run with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.config import STATIC_DIR, get_settings
from app.core.errors import register_exception_handlers
from app.database import init_db
from app.routers import auth, collections, dashboard, items, metadata, pages, profile, recommendations

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

ROUTERS = [
    pages.router,
    auth.router,
    profile.router,
    profile.api_router,
    dashboard.router,
    dashboard.api_router,
    items.router,
    items.api_router,
    collections.router,
    collections.api_router,
    metadata.router,
    recommendations.router,
    recommendations.api_router,
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create database tables on start-up (safe to run repeatedly)."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Application factory: configures middleware, static files, routes and error handlers."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        description=settings.tagline,
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    @application.middleware("http")
    async def add_security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    # Added last so it wraps everything else: the session is available to all routes.
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="curio_session",
        max_age=settings.session_max_age,
        same_site="lax",
        https_only=settings.secure_cookies,
    )

    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    for router in ROUTERS:
        application.include_router(router)

    register_exception_handlers(application)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Lightweight liveness check."""
        return {"status": "ok", "app": settings.app_name, "version": __version__}

    return application


app = create_app()
