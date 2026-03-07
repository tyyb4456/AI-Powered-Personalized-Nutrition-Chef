"""
api/schemas/auth_schemas.py

Request / response models for auth and user endpoints.
Kept separate from the internal nutrition_schemas.py so the API
contract stays stable even if internal models evolve.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, EmailStr


# ═══════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    name:     str            = Field(..., min_length=2, max_length=100, examples=["Ali Khan"])
    email:    Optional[EmailStr] = Field(default=None,  examples=["ali@example.com"])
    password: str            = Field(..., min_length=6,  examples=["securepass123"])


class LoginRequest(BaseModel):
    name:     str = Field(..., examples=["Ali Khan"])
    password: str = Field(..., examples=["securepass123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      str
    name:         str


# ═══════════════════════════════════════════════════════════════
# USER PROFILE
# ═══════════════════════════════════════════════════════════════

class UpdateProfileRequest(BaseModel):
    age:            Optional[int]   = Field(default=None, ge=1,    le=120)
    gender:         Optional[str]   = Field(default=None, examples=["male", "female", "other"])
    weight_kg:      Optional[float] = Field(default=None, ge=20,   le=300)
    height_cm:      Optional[float] = Field(default=None, ge=50,   le=250)
    activity_level: Optional[str]   = Field(default=None, examples=["sedentary", "light", "moderate", "active", "very_active"])
    fitness_goal:   Optional[str]   = Field(default=None, examples=["fat_loss", "muscle_gain", "maintenance"])

    allergies:      Optional[list[str]] = Field(default=None, examples=[["nuts", "dairy"]])
    medical_conditions: Optional[list[str]] = Field(
        default=None,
        examples=[["diabetes", "hypertension"]],
        description="Any of: diabetes, hypertension, celiac, lactose_intolerance, kidney_disease, heart_disease, ibs, anemia, osteoporosis"
    )

    # Preferences
    cuisine:        Optional[str]   = Field(default=None, examples=["pakistani"])
    spice_level:    Optional[str]   = Field(default=None, examples=["medium"])


class UserProfileResponse(BaseModel):
    user_id:        str
    name:           str
    email:          Optional[str]   = None

    # Physical stats
    age:            Optional[int]   = None
    gender:         Optional[str]   = None
    weight_kg:      Optional[float] = None
    height_cm:      Optional[float] = None
    activity_level: Optional[str]   = None
    fitness_goal:   Optional[str]   = None

    # Health data
    allergies:          list[str] = Field(default_factory=list)
    medical_conditions: list[str] = Field(default_factory=list)

    # Preferences
    preferences: dict = Field(default_factory=dict)

    # Goal
    calorie_target: Optional[int]   = None
    goal_type:      Optional[str]   = None
    macro_split:    Optional[dict]  = None


# ═══════════════════════════════════════════════════════════════
# GENERIC WRAPPERS
# ═══════════════════════════════════════════════════════════════

class SuccessResponse(BaseModel):
    message: str
    data:    Optional[dict] = None