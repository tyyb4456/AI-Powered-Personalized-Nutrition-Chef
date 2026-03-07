"""
api/routers/users.py

User profile endpoints:
  GET  /users/me         — fetch current user's full profile
  PUT  /users/me         — update profile, allergies, medical conditions, preferences
  GET  /users/me/goals   — get current calorie/macro goal
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from schemas.auth_schemas import UpdateProfileRequest, UserProfileResponse
from db.models import User
from db.repositories import UserRepository
from schemas.nutrition_schemas import MedicalCondition, MedicalConditionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

VALID_CONDITIONS: list[str] = [
    "diabetes", "hypertension", "celiac", "lactose_intolerance",
    "kidney_disease", "heart_disease", "ibs", "anemia", "osteoporosis",
]

VALID_ACTIVITY_LEVELS: list[str] = [
    "sedentary", "light", "moderate", "active", "very_active",
]


# ── GET /users/me ─────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user's profile",
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the full profile for the authenticated user including:
    physical stats, fitness goal, allergies, medical conditions, and preferences.
    """
    repo    = UserRepository(db)
    profile = db.query(__import__("db.models", fromlist=["UserProfile"]).UserProfile)\
                .filter_by(user_id=current_user.id).first()
    goal    = repo.get_current_goal(current_user.id)
    conditions = repo.get_medical_conditions(current_user.id)
    allergies  = repo.get_allergies(current_user.id)
    prefs      = repo.get_preferences(current_user.id)

    # Strip internal keys
    public_prefs = {k: v for k, v in prefs.items() if not k.startswith("__")}

    return UserProfileResponse(
        user_id   = current_user.id,
        name      = current_user.name,
        email     = current_user.email,
        age            = profile.age            if profile else None,
        gender         = profile.gender         if profile else None,
        weight_kg      = profile.weight_kg      if profile else None,
        height_cm      = profile.height_cm      if profile else None,
        activity_level = profile.activity_level if profile else None,
        fitness_goal   = public_prefs.get("fitness_goal"),
        allergies      = allergies,
        medical_conditions = [c.condition for c in conditions],
        preferences    = public_prefs,
        calorie_target = goal.calorie_target if goal else None,
        goal_type      = goal.goal_type      if goal else None,
        macro_split    = {
            "protein": goal.protein_pct,
            "carbs":   goal.carbs_pct,
            "fat":     goal.fat_pct,
        } if goal else None,
    )


# ── PUT /users/me ─────────────────────────────────────────────────────────────

@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user's profile",
)
def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update any subset of profile fields. Only provided fields are changed.

    **Medical conditions** must be one of:
    `diabetes, hypertension, celiac, lactose_intolerance, kidney_disease,
    heart_disease, ibs, anemia, osteoporosis`
    """
    repo = UserRepository(db)

    # ── Physical stats ────────────────────────────────────────────────────────
    # Only upsert if at least one physical field is present in the request
    physical_fields = [payload.age, payload.gender, payload.weight_kg,
                       payload.height_cm, payload.activity_level]
    if any(f is not None for f in physical_fields):
        from db.models import UserProfile
        existing = db.query(UserProfile).filter_by(user_id=current_user.id).first()

        # Merge with existing values
        repo.upsert_profile(
            user_id        = current_user.id,
            age            = payload.age            or (existing.age            if existing else 25),
            gender         = payload.gender         or (existing.gender         if existing else "other"),
            weight_kg      = payload.weight_kg      or (existing.weight_kg      if existing else 70.0),
            height_cm      = payload.height_cm      or (existing.height_cm      if existing else 170.0),
            activity_level = payload.activity_level or (existing.activity_level if existing else "moderate"),
        )

    # ── Validate and sync activity_level ──────────────────────────────────────
    if payload.activity_level and payload.activity_level not in VALID_ACTIVITY_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity_level. Must be one of: {VALID_ACTIVITY_LEVELS}",
        )

    # ── Allergies ─────────────────────────────────────────────────────────────
    if payload.allergies is not None:
        repo.sync_allergies(current_user.id, payload.allergies)

    # ── Medical conditions ────────────────────────────────────────────────────
    if payload.medical_conditions is not None:
        invalid = [c for c in payload.medical_conditions if c not in VALID_CONDITIONS]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown medical conditions: {invalid}. Valid: {VALID_CONDITIONS}",
            )
        conditions = [
            MedicalCondition(condition=c)  # type: ignore[arg-type]
            for c in payload.medical_conditions
        ]
        repo.sync_medical_conditions(current_user.id, conditions)

    # ── Preferences (cuisine, spice_level, fitness_goal) ──────────────────────
    if payload.cuisine:
        repo.upsert_preference(current_user.id, "cuisine",       payload.cuisine)
    if payload.spice_level:
        repo.upsert_preference(current_user.id, "spice_level",   payload.spice_level)
    if payload.fitness_goal:
        repo.upsert_preference(current_user.id, "fitness_goal",  payload.fitness_goal)

    db.flush()

    logger.info("Profile updated for user %s", current_user.id)

    # Return the refreshed profile
    return get_my_profile(current_user=current_user, db=db)