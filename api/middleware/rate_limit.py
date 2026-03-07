"""
api/middleware/rate_limit.py

FastAPI middleware that enforces per-user LLM rate limits via Redis.

Strategy:
  - LLM-heavy endpoints (recipe generate, meal plan generate, progress report,
    image analysis, learning loop) are "metered" — each call costs 1 token.
  - Limit: RATE_LIMIT_MAX_CALLS per hour per user (default 20, env-configurable).
  - Header X-RateLimit-Limit / X-RateLimit-Remaining / X-RateLimit-Reset are
    added to ALL responses so clients can track their budget.
  - If Redis is down the middleware allows all requests (fail-open).
  - Unauthenticated requests are not rate-limited here (auth middleware handles 401).

Two layers of integration:
  1. This Starlette BaseHTTPMiddleware attaches rate-limit headers to every response.
  2. A FastAPI Depends() check_llm_rate_limit() raises 429 before the LLM call
     on the expensive endpoints. This keeps the middleware lightweight.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

RATE_LIMIT_MAX_CALLS: int = int(os.getenv("RATE_LIMIT_MAX_CALLS", "20"))
RATE_LIMIT_WINDOW_SEC: int = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "3600"))   # 1 hour


# ─────────────────────────────────────────────────────────────────────────────
# Helper: extract user_id from JWT without re-running full auth
# ─────────────────────────────────────────────────────────────────────────────

def _extract_user_id(request: Request) -> Optional[str]:
    """
    Quick JWT decode to get user_id for rate-limit key.
    Returns None if token is missing or malformed (let auth handle the error).
    Deliberately avoids DB lookups — only decodes the token payload.
    """
    auth: str = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        from core.security import decode_access_token
        payload = decode_access_token(token)
        return payload.get("sub") if payload else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Middleware — adds X-RateLimit-* headers to all responses
# ─────────────────────────────────────────────────────────────────────────────

class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """
    Injects X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
    headers into every response for authenticated users.

    Does NOT block requests — just provides information.
    The Depends() check below does the actual blocking for LLM endpoints.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        user_id = _extract_user_id(request)
        if not user_id:
            return response

        try:
            from cache.redis_client import redis_client
            status_info = redis_client.get_rate_limit_status(user_id)

            response.headers["X-RateLimit-Limit"]     = str(RATE_LIMIT_MAX_CALLS)
            response.headers["X-RateLimit-Remaining"] = str(status_info.get("calls_remaining", RATE_LIMIT_MAX_CALLS))
            response.headers["X-RateLimit-Window"]    = f"{RATE_LIMIT_WINDOW_SEC}s"
        except Exception as e:
            logger.debug("Could not attach rate-limit headers: %s", e)

        return response


# ─────────────────────────────────────────────────────────────────────────────
# Dependency — blocks LLM endpoint if limit exceeded
# ─────────────────────────────────────────────────────────────────────────────

def check_llm_rate_limit(request: Request) -> None:
    """
    FastAPI Depends() — call this on any LLM-heavy endpoint.

    Raises HTTP 429 if the user has exceeded their hourly call budget.
    Fails open (allows) if Redis is unavailable.

    Usage:
        @router.post("/recipes/generate")
        async def generate(
            _: None = Depends(check_llm_rate_limit),
            ...
        ):
    """
    user_id = _extract_user_id(request)
    if not user_id:
        return   # unauthenticated — let normal auth handle it

    try:
        from cache.redis_client import redis_client
        allowed, count = redis_client.check_rate_limit(user_id)
        if not allowed:
            remaining_ttl = _get_ttl(user_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error":         "rate_limit_exceeded",
                    "message":       f"You have used all {RATE_LIMIT_MAX_CALLS} LLM calls for this hour.",
                    "calls_used":    count,
                    "calls_limit":   RATE_LIMIT_MAX_CALLS,
                    "retry_after_s": remaining_ttl,
                },
                headers={"Retry-After": str(remaining_ttl)},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Rate limit check failed (%s) — allowing request.", e)


def _get_ttl(user_id: str) -> int:
    """Return seconds until the rate-limit window resets. Falls back to window size."""
    try:
        from cache.redis_client import redis_client
        if redis_client.available:
            ttl = redis_client._client.ttl(f"rate_limit:{user_id}")
            return max(ttl, 0)
    except Exception:
        pass
    return RATE_LIMIT_WINDOW_SEC