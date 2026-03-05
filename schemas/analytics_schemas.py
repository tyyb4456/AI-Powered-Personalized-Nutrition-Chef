"""
api/schemas/analytics_schemas.py

Request / response models for:
  - Weekly progress reports (LLM-generated)
  - Learned preferences (CRUD)
  - Trigger learning loop on demand
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# PROGRESS REPORT
# ═══════════════════════════════════════════════════════════════

class GenerateProgressReportRequest(BaseModel):
    """
    All optional — defaults loaded from the user's saved profile.
    """
    days:           int           = Field(default=7,  ge=1, le=30,   description="How many days of logs to analyse")
    calorie_target: Optional[int] = Field(default=None, ge=500, le=5000, description="Override saved calorie target")


class ProgressReportResponse(BaseModel):
    week_start:          str
    week_end:            str
    avg_adherence_pct:   float
    best_day:            str
    worst_day:           str
    patterns_identified: list[str]
    recommendations:     list[str]
    goal_progress:       str
    motivational_note:   str
    # Extra context injected by the API (not from LLM)
    logs_analysed:       int
    calorie_target_used: int


# ═══════════════════════════════════════════════════════════════
# LEARNED PREFERENCES
# ═══════════════════════════════════════════════════════════════

class LearnedPreferencesResponse(BaseModel):
    liked_ingredients:    list[str]
    disliked_ingredients: list[str]
    preferred_textures:   list[str]
    preferred_cuisines:   list[str]
    avoided_cuisines:     list[str]
    spice_preference:     Optional[str]
    goal_refinement:      Optional[str]
    session_insights:     list[str]


class UpdateLearnedPreferencesRequest(BaseModel):
    """
    Manually update individual preference fields.
    Only provided fields are changed — omitted fields are preserved.
    """
    liked_ingredients:    Optional[list[str]] = None
    disliked_ingredients: Optional[list[str]] = None
    preferred_textures:   Optional[list[str]] = None
    preferred_cuisines:   Optional[list[str]] = None
    avoided_cuisines:     Optional[list[str]] = None
    spice_preference:     Optional[str]       = None
    goal_refinement:      Optional[str]       = None
    session_insights:     Optional[list[str]] = None


# ═══════════════════════════════════════════════════════════════
# TRIGGER LEARNING LOOP
# ═══════════════════════════════════════════════════════════════

class TriggerLearningRequest(BaseModel):
    """
    Manually trigger the learning loop agent on a specific feedback entry.
    The LLM reads the rating + comment and updates learned preferences.
    """
    feedback_id: str = Field(..., description="ID of a feedback entry to learn from")


class TriggerLearningResponse(BaseModel):
    message:              str
    preferences_updated:  bool
    goal_updated:         bool
    updated_preferences:  LearnedPreferencesResponse