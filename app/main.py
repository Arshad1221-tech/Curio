"""FastAPI application entry point for Curio.

Run with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.config import get_settings
from app.database import init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create database tables on start-up (safe to run repeatedly)."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Application factory: configures middleware and routes."""
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

    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="curio_session",
        max_age=settings.session_max_age,
        same_site="lax",
        https_only=settings.secure_cookies,
    )

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Lightweight liveness check."""
        return {"status": "ok", "app": settings.app_name, "version": __version__}

    return application


app = create_app()
