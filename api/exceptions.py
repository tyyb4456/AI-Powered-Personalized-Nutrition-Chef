"""
api/exceptions.py  (Phase 7 — standardised error envelope)

Every API error returns the same JSON shape:

  {
    "error":   "not_found",
    "message": "Recipe 'abc' not found.",
    "detail":  {...},      <- optional field-level or context detail
    "path":    "/recipes/abc",
    "status":  404
  }

Machine-readable `error` codes let clients handle errors programmatically
without parsing human-readable messages.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

ENV = os.getenv("ENV", "development")


# ── Error envelope ────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error:   str
    message: str
    detail:  Optional[Any] = None
    path:    Optional[str] = None
    status:  int


_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limit_exceeded",
    500: "internal_server_error",
    503: "service_unavailable",
}


def _code_for(http_status: int) -> str:
    return _STATUS_CODES.get(http_status, "error")


def _make(
    request: Request,
    http_status: int,
    error_code: str,
    message: str,
    detail: Any = None,
) -> JSONResponse:
    body = ErrorResponse(
        error   = error_code,
        message = message,
        detail  = detail,
        path    = str(request.url.path),
        status  = http_status,
    )
    return JSONResponse(status_code=http_status, content=body.model_dump())


# ── Handler registration ──────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            message     = detail.get("message", str(detail))
            body_detail = {k: v for k, v in detail.items() if k != "message"} or None
        else:
            message     = str(detail) if detail else "An error occurred."
            body_detail = None

        logger.warning("HTTP %d %s %s — %s", exc.status_code, request.method, request.url.path, message)
        return _make(request, exc.status_code, _code_for(exc.status_code), message, body_detail)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        simplified = [
            {
                "field":   " → ".join(str(loc) for loc in err["loc"] if loc != "body"),
                "message": err["msg"],
                "type":    err["type"],
            }
            for err in exc.errors()
        ]
        logger.debug("Validation error %s %s: %d field(s)", request.method, request.url.path, len(simplified))
        return _make(
            request, 422, "validation_error",
            f"Request validation failed on {len(simplified)} field(s).",
            simplified,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("DB IntegrityError: %s", exc.orig)
        return _make(request, 409, "conflict", "A record with this data already exists.")

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _make(
            request, 500, "internal_server_error",
            "An unexpected error occurred. Please try again later.",
            # Only include detail in dev mode — never expose stack traces in production
            str(exc) if ENV == "development" else None,
        )