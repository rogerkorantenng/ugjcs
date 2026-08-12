"""RFC 9457 problem-details responses.

Domain errors carry no HTTP semantics of their own. Translating them into status codes
is an infrastructure concern, and this module is the single place that does it, so no
route can invent its own inconsistent error shape.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ugjcs.domain.errors import (
    AuthorizationDeniedError,
    DomainError,
    GuardViolationError,
    IllegalTransitionError,
)

PROBLEM_MEDIA_TYPE = "application/problem+json"

# Ordered by specificity: an unlisted `DomainError` subclass falls through to 400, which
# is the correct default for "the request was well-formed but the domain rejected it."
_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    IllegalTransitionError: status.HTTP_409_CONFLICT,
    GuardViolationError: status.HTTP_409_CONFLICT,
    AuthorizationDeniedError: status.HTTP_403_FORBIDDEN,
}


def _status_for(error: DomainError) -> int:
    for error_type, code in _STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return code
    # `AuthenticationError` (application.identity) and `InvalidTokenError`
    # (infrastructure.security.tokens) are matched by class name rather than imported:
    # importing `ugjcs.infrastructure.security.tokens` here alongside `application.identity`
    # would mean this module reaches into two different layers for one conceptual job
    # (mapping domain-shaped errors to status codes). Name matching keeps this module
    # dependent on `ugjcs.domain` alone.
    if type(error).__name__ in {"AuthenticationError", "InvalidTokenError"}:
        return status.HTTP_401_UNAUTHORIZED
    if type(error).__name__ == "AccountError":
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_400_BAD_REQUEST


def _problem(status_code: int, title: str, detail: str, *, instance: str) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    return JSONResponse(status_code=status_code, content=body, media_type=PROBLEM_MEDIA_TYPE)


def register_exception_handlers(app: FastAPI) -> None:
    """Wire every `DomainError`, every `HTTPException`, and validation failures alike."""

    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            _status_for(exc), type(exc).__name__, str(exc), instance=str(request.url.path)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(
            exc.status_code,
            exc.__class__.__name__,
            str(exc.detail),
            instance=str(request.url.path),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RequestValidationError",
            "the request body failed validation",
            instance=str(request.url.path),
        )
