"""
api/routers/auth.py

Authentication endpoints:
  POST /auth/register  — create a new user account
  POST /auth/login     — exchange credentials for a JWT

Password is stored as a bcrypt hash in user_preferences table
(key = "__password_hash__") to avoid schema changes to the
existing users table. A dedicated `password_hash` column can be
added via Alembic migration in a future phase.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db
from core.security import hash_password, verify_password, create_access_token
from schemas.auth_schemas import RegisterRequest, LoginRequest, TokenResponse
from db.repositories import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

_PASSWORD_PREF_KEY = "__password_hash__"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_password(repo: UserRepository, user_id: str, plain: str) -> None:
    """Store hashed password in user_preferences (no schema change needed)."""
    repo.upsert_preference(user_id, _PASSWORD_PREF_KEY, hash_password(plain))


def _get_password_hash(repo: UserRepository, user_id: str) -> str | None:
    prefs = repo.get_preferences(user_id)
    return prefs.get(_PASSWORD_PREF_KEY)


# ── Register ──────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.

    - **name**: display name (must be unique)
    - **email**: optional, stored for future use
    - **password**: min 6 characters, stored as bcrypt hash
    """
    repo = UserRepository(db)

    # ── Name uniqueness check ─────────────────────────────────────────────────
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user named '{payload.name}' already exists. Choose a different name or log in.",
        )

    # ── Create user ───────────────────────────────────────────────────────────
    user = repo.create(name=payload.name, email=payload.email)
    _save_password(repo, user.id, payload.password)

    db.flush()   # ensure user.id is available

    token = create_access_token(user_id=user.id, extra_claims={"name": user.name})

    logger.info("New user registered: %s (%s)", user.name, user.id)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with name + password.

    Returns a Bearer token valid for 24 hours.
    """
    repo = UserRepository(db)

    user = repo.get_by_name(payload.name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid name or password.",
        )

    stored_hash = _get_password_hash(repo, user.id)
    if not stored_hash or not verify_password(payload.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid name or password.",
        )

    token = create_access_token(user_id=user.id, extra_claims={"name": user.name})

    logger.info("User logged in: %s (%s)", user.name, user.id)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
    )