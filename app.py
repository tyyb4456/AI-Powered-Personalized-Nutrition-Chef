"""
api/app.py

FastAPI application factory.

Usage:
  uvicorn api.app:app --reload --port 8000
  # or from project root:
  uvicorn api.app:app --reload

Environment variables (set in .env):
  DATABASE_URL                — PostgreSQL connection string
  SECRET_KEY                  — JWT signing secret
  ACCESS_TOKEN_EXPIRE_MINUTES — JWT lifetime (default 1440 = 24h)
  ENV                         — "development" | "production"
  CORS_ORIGINS                — comma-separated allowed origins
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from exceptions import register_exception_handlers


logger = logging.getLogger(__name__)

# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run setup on startup, teardown on shutdown."""
    logger.info("🚀 Nutrition AI API starting up...")

    # Verify DB connection
    try:
        from db.database import engine
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error("❌ Database connection failed: %s", e)

    # Verify Redis connection (optional)
    try:
        from cache.redis_client import redis_client
        redis_client.client.ping()
        logger.info("✅ Redis connection verified")
    except Exception:
        logger.warning("⚠️  Redis not available — caching disabled")

    yield

    logger.info("🛑 Nutrition AI API shutting down...")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title       = "Nutrition AI API",
        description = (
            "Personalized AI-powered nutrition and meal planning API.\n\n"
            "Built on LangGraph + Gemini 2.5 Flash with PostgreSQL, Redis, and ChromaDB."
        ),
        version     = "1.0.0",
        docs_url    = "/docs",
        redoc_url   = "/redoc",
        lifespan    = lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins     = origins,
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    from routers import auth, users, recipes, meal_plans, feedback, meal_logs, analytics
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(recipes.router)
    app.include_router(meal_plans.router)
    app.include_router(feedback.router)
    app.include_router(meal_logs.router)
    app.include_router(analytics.router)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], summary="Health check")
    def health_check():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/", tags=["System"], include_in_schema=False)
    def root():
        return {
            "message": "Nutrition AI API is running.",
            "docs": "/docs",
            "health": "/health",
        }

    return app


# ── App instance ──────────────────────────────────────────────────────────────

app = create_app()