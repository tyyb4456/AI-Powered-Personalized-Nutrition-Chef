"""
api/exceptions.py

Global exception handlers registered on the FastAPI app.

Converts common exceptions into consistent JSON error responses:
  {
    "error":   "human-readable message",
    "detail":  "technical detail (dev mode only)",
    "code":    HTTP status code
  }
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

DEV_MODE = os.getenv("ENV", "development") == "development"


def _error_response(message: str, code: int, detail: str = "") -> JSONResponse:
    body: dict = {"error": message, "code": code}
    if DEV_MODE and detail:
        body["detail"] = detail
    return JSONResponse(status_code=code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Call this once during app startup to attach all handlers."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Pydantic validation failures → 422 with readable field errors."""
        errors = []
        for err in exc.errors():
            loc   = " → ".join(str(x) for x in err["loc"] if x != "body")
            msg   = err["msg"]
            errors.append(f"{loc}: {msg}" if loc else msg)
        return _error_response(
            message="; ".join(errors),
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(IntegrityError)
    async def db_integrity_handler(request: Request, exc: IntegrityError):
        """DB unique constraint violations → 409 Conflict."""
        logger.warning("DB IntegrityError: %s", exc.orig)
        return _error_response(
            message="A record with this data already exists.",
            code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return _error_response(
            message=str(exc),
            code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _error_response(
            message="An unexpected error occurred. Please try again.",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )