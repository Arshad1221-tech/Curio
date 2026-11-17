"""Domain exceptions and global exception handlers.

Browser requests receive friendly HTML error pages; ``/api`` requests receive
JSON error bodies.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("curio.errors")


# --- Domain exceptions -----------------------------------------------------------
class CurioError(Exception):
    """Base class for expected, user-facing errors raised by the service layer."""

    status_code = 400
    title = "Something went wrong"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message or self.title


class NotFoundError(CurioError):
    status_code = 404
    title = "Not found"


class ConflictError(CurioError):
    status_code = 409
    title = "Already exists"


class PermissionDeniedError(CurioError):
    status_code = 403
    title = "Access denied"


class ExternalServiceError(CurioError):
    status_code = 502
    title = "External service unavailable"


class ServiceNotConfiguredError(CurioError):
    status_code = 503
    title = "Service not configured"


class LoginRequired(Exception):
    """Raised by auth dependencies when a page needs a signed-in user."""

    def __init__(self, next_url: str = "/dashboard") -> None:
        super().__init__("Login required")
        self.next_url = next_url


# --- Helpers ---------------------------------------------------------------------
ERROR_TITLES = {
    400: "Bad request",
    401: "Please log in",
    403: "Access denied",
    404: "Page not found",
    405: "Method not allowed",
    409: "Already exists",
    422: "Invalid input",
    500: "Unexpected error",
    502: "External service unavailable",
    503: "Service unavailable",
}


def wants_json(request: Request) -> bool:
    if request.url.path.startswith("/api/"):
        return True
    accept = request.headers.get("accept", "")
    return "application/json" in accept and "text/html" not in accept


def _error_page(request: Request, status_code: int, message: str) -> Response:
    from app.core.templating import render  # local import avoids a circular import

    try:
        return render(
            request,
            "errors/error.html",
            {
                "status_code": status_code,
                "error_title": ERROR_TITLES.get(status_code, "Error"),
                "error_message": message,
            },
            status_code=status_code,
        )
    except Exception:  # pragma: no cover - last-resort fallback
        logger.exception("Failed to render error page")
        return Response(f"{status_code} - {message}", status_code=status_code, media_type="text/plain")


def _respond(request: Request, status_code: int, message: str) -> Response:
    if wants_json(request):
        return JSONResponse({"detail": message}, status_code=status_code)
    return _error_page(request, status_code, message)


# --- Registration ----------------------------------------------------------------
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LoginRequired)
    async def handle_login_required(request: Request, exc: LoginRequired) -> Response:
        if wants_json(request):
            return JSONResponse({"detail": "Authentication required."}, status_code=401)
        return RedirectResponse(f"/login?next={quote(exc.next_url, safe='/')}", status_code=303)

    @app.exception_handler(CurioError)
    async def handle_curio_error(request: Request, exc: CurioError) -> Response:
        return _respond(request, exc.status_code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> Response:
        message = exc.detail if isinstance(exc.detail, str) else ERROR_TITLES.get(exc.status_code, "Error")
        if exc.status_code == 404 and not isinstance(exc.detail, str):
            message = "We couldn't find the page you were looking for."
        elif exc.status_code == 404 and exc.detail == "Not Found":
            message = "We couldn't find the page you were looking for."
        return _respond(request, exc.status_code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> Response:
        errors = exc.errors()
        if wants_json(request):
            return JSONResponse({"detail": jsonable_encoder(errors)}, status_code=422)
        # A malformed path parameter (e.g. /items/abc) is effectively a missing page.
        if any(err.get("loc", [None])[0] == "path" for err in errors):
            return _error_page(request, 404, "We couldn't find the page you were looking for.")
        return _error_page(request, 400, "Some of the information sent was invalid. Please check the form and try again.")

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> Response:
        logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
        return _respond(request, 500, "An unexpected error occurred. Please try again in a moment.")
