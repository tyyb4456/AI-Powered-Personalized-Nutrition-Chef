"""
api/app.py  (Phase 7 — production polish)

Changes from Phase 6:
  - RateLimitHeaderMiddleware added (injects X-RateLimit-* headers)
  - Trusted host / security headers middleware
  - Enhanced /health endpoint with dependency checks
  - OpenAPI metadata enriched (tags, contact, license, servers)
  - Logging configured from ENV
  - Version bumped to 1.0.0
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from exceptions import register_exception_handlers

ENV      = os.getenv("ENV", "development")
LOG_LEVEL = logging.DEBUG if ENV == "development" else logging.INFO
logging.basicConfig(
    level   = LOG_LEVEL,
    format  = "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Nutrition AI API starting up [env=%s]...", ENV)

    try:
        from db.database import engine
        import sqlalchemy
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        logger.info("✅ PostgreSQL connected")
    except Exception as e:
        logger.error("❌ PostgreSQL connection failed: %s", e)

    try:
        from cache.redis_client import redis_client
        if redis_client.available:
            logger.info("✅ Redis connected")
        else:
            logger.warning("⚠️  Redis unavailable — rate limiting + caching disabled")
    except Exception:
        logger.warning("⚠️  Redis check failed")

    yield

    logger.info("🛑 Nutrition AI API shutting down...")


# ── OpenAPI metadata ──────────────────────────────────────────────────────────

DESCRIPTION = """
## Nutrition AI API

Personalized AI-powered nutrition and meal planning.

### Features
- 🍽️ **Recipe generation** — personalized recipes via Gemini 2.5 Flash + LangGraph
- 📅 **Weekly meal plans** — 7-day plans with grocery lists and prep schedules
- 📊 **Progress tracking** — meal logging, calorie adherence, weekly reports
- 📷 **Food image analysis** — identify meals and estimate nutrition from photos
- 🧠 **Learning loop** — preferences evolve with every feedback submission
- 🔒 **JWT authentication** — secure per-user data isolation

### Rate Limits
LLM-powered endpoints are rate-limited to **20 calls/hour** per user (configurable).
Check the `X-RateLimit-Remaining` response header to track your budget.

### Authentication
All endpoints (except `/auth/register` and `/auth/login`) require a Bearer JWT.
Obtain a token via `POST /auth/login`.
"""

TAGS_METADATA = [
    {"name": "Authentication",        "description": "Register and log in"},
    {"name": "Users",                 "description": "Profile management"},
    {"name": "Recipes",               "description": "AI recipe generation"},
    {"name": "Meal Plans",            "description": "7-day meal planning"},
    {"name": "Feedback",              "description": "Recipe ratings and comments"},
    {"name": "Meal Logs",             "description": "Log consumed meals"},
    {"name": "Analytics & Learning",  "description": "Progress reports and learned preferences"},
    {"name": "Food Image Analysis",   "description": "Identify food from photos"},
    {"name": "System",                "description": "Health check and status"},
]


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title          = "Nutrition AI API",
        description    = DESCRIPTION,
        version        = "1.0.0",
        docs_url       = "/docs",
        redoc_url      = "/redoc",
        openapi_url    = "/openapi.json",
        openapi_tags   = TAGS_METADATA,
        lifespan       = lifespan,
        contact        = {"name": "Nutrition AI", "email": "support@nutrition-ai.example.com"},
        license_info   = {"name": "MIT"},
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    origins     = [o.strip() for o in raw_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = origins,
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
        expose_headers    = ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Window"],
    )

    # ── Trusted hosts (production guard) ──────────────────────────────────────
    if ENV == "production":
        allowed_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # ── Rate limit headers middleware ─────────────────────────────────────────
    from middleware.rate_limit import RateLimitHeaderMiddleware
    app.add_middleware(RateLimitHeaderMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    from routers import auth, users, recipes, meal_plans, feedback, meal_logs, analytics, images
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(recipes.router)
    app.include_router(meal_plans.router)
    app.include_router(feedback.router)
    app.include_router(meal_logs.router)
    app.include_router(analytics.router)
    app.include_router(images.router)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], summary="Health check")
    def health_check():
        """
        Lightweight liveness probe — returns immediately without DB or Redis I/O.
        Use `/health/ready` for a full readiness probe.
        """
        return {"status": "ok", "version": "1.0.0", "env": ENV}

    @app.get("/health/ready", tags=["System"], summary="Readiness probe")
    def readiness_check():
        """
        Full readiness probe — checks PostgreSQL and Redis connectivity.
        Returns 503 if any critical dependency is unavailable.
        Suitable for Kubernetes readinessProbe.
        """
        from fastapi import HTTPException

        checks: dict = {}
        overall_ok   = True

        # PostgreSQL
        try:
            from db.database import engine
            import sqlalchemy
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as e:
            checks["postgres"] = f"error: {e}"
            overall_ok = False

        # Redis (non-critical — degraded OK)
        try:
            from cache.redis_client import redis_client
            checks["redis"] = "ok" if redis_client.available else "unavailable (non-critical)"
        except Exception as e:
            checks["redis"] = f"error: {e}"

        if not overall_ok:
            raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})

        return {"status": "ready", "checks": checks, "version": "1.0.0"}

    @app.get("/", tags=["System"], include_in_schema=False)
    def root():
        return {
            "message": "Nutrition AI API is running.",
            "docs":    "/docs",
            "health":  "/health",
            "ready":   "/health/ready",
            "version": "1.0.0",
        }

    return app


# ── App instance ──────────────────────────────────────────────────────────────
app = create_app()