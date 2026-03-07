"""
api/schemas/tracking_schemas.py

Request / response models for:
  - Feedback (recipe ratings + comments)
  - Meal logging (what was actually eaten)
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# FEEDBACK
# ═══════════════════════════════════════════════════════════════

class SubmitFeedbackRequest(BaseModel):
    recipe_id: str   = Field(..., description="ID of the recipe being rated")
    rating:    int   = Field(..., ge=1, le=5, description="Star rating 1-5")
    comment:   Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional free-text comment or suggestion",
        examples=["Loved the spices, but could use more protein!"],
    )


class FeedbackResponse(BaseModel):
    feedback_id: str
    recipe_id:   str
    rating:      int
    comment:     Optional[str]
    created_at:  str


class FeedbackListResponse(BaseModel):
    feedback:    list[FeedbackResponse]
    total:       int


# ═══════════════════════════════════════════════════════════════
# MEAL LOG
# ═══════════════════════════════════════════════════════════════

class LogMealRequest(BaseModel):
    log_date:  str  = Field(
        ...,
        description="ISO date of the meal e.g. '2026-03-01'",
        examples=["2026-03-01"],
    )
    meal_slot: str  = Field(
        ...,
        description="One of: breakfast, lunch, dinner, snack",
        examples=["lunch"],
    )
    dish_name: str  = Field(..., max_length=200, examples=["Chicken Karahi"])
    planned:   bool = Field(
        default=False,
        description="True if this was a planned meal from an active meal plan",
    )
    calories:  int   = Field(..., ge=0,  le=5000)
    protein_g: float = Field(..., ge=0)
    carbs_g:   float = Field(..., ge=0)
    fat_g:     float = Field(..., ge=0)
    source:    str   = Field(
        default="manual",
        description="How this was logged: manual / image / plan",
        examples=["manual"],
    )
    # Optional: link to a saved recipe
    recipe_id: Optional[str] = Field(
        default=None,
        description="If this meal matches a saved recipe, link its ID here",
    )


class MealLogResponse(BaseModel):
    log_id:    str
    log_date:  str
    meal_slot: str
    dish_name: str
    planned:   bool
    calories:  int
    protein_g: float
    carbs_g:   float
    fat_g:     float
    source:    str
    logged_at: str


class MealLogListResponse(BaseModel):
    logs:       list[MealLogResponse]
    total:      int
    date_from:  Optional[str] = None
    date_to:    Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# DAILY ADHERENCE
# ═══════════════════════════════════════════════════════════════

class DailyAdherenceResponse(BaseModel):
    log_date:         str
    planned_calories: int
    actual_calories:  int
    adherence_pct:    float
    meals_logged:     int
    meals_skipped:    int