"""
db/database.py

Database engine + session factory.

Usage
-----
# In agent / repository code:
from db.database import get_db

with get_db() as db:
    user = db.query(User).filter_by(id="...").first()

# In FastAPI (Phase 5):
from db.database import get_db_dep   # yields a session per request
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from db.models import Base


# ── Connection string ─────────────────────────────────────────────────────────
# Reads from environment. Falls back to a local dev DB.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:tybpost%40%2356*@localhost:5432/nutrition_ai",
)

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    echo=False,             # set True to see SQL in terminal during dev
    pool_pre_ping=True,     # check connection health before each use
    pool_size=5,
    max_overflow=10,
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # keep object data after commit (safer for agents)
)


# ── Context manager — use in agents and repositories ─────────────────────────

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Yields a database session and guarantees cleanup.

    Example:
        with get_db() as db:
            db.add(user)
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── FastAPI dependency (Phase 5) ──────────────────────────────────────────────

def get_db_dep() -> Generator[Session, None, None]:
    """
    FastAPI Depends() compatible generator.
    Use as: db: Session = Depends(get_db_dep)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Table creation (dev / test only) ─────────────────────────────────────────

def create_tables() -> None:
    """
    Create all tables from ORM models.
    Use Alembic migrations in production — this is for dev/testing only.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created.")


def drop_tables() -> None:
    """Drop all tables. DANGEROUS — dev/test only."""
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All tables dropped.")