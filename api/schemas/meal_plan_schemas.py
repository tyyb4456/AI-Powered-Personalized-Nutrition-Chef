"""
api/schemas/meal_plan_schemas.py

Request / response models for meal plan, grocery, and prep schedule endpoints.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# REQUEST
# ═══════════════════════════════════════════════════════════════

class GenerateMealPlanRequest(BaseModel):
    """
    All fields optional — loaded from the user's saved DB profile.
    Providing them here overrides the profile for this request only.
    """
    fitness_goal:    Optional[str]  = Field(default=None, examples=["muscle_gain"])
    cuisine:         Optional[str]  = Field(default=None, examples=["pakistani"])
    spice_level:     Optional[str]  = Field(default=None, examples=["medium"])
    extra_allergies: list[str]      = Field(default_factory=list)
    week_start:      Optional[str]  = Field(
        default=None,
        description="ISO date for the Monday that starts this plan (e.g. '2026-03-02'). "
                    "Defaults to next Monday if not provided.",
        examples=["2026-03-02"],
    )


# ═══════════════════════════════════════════════════════════════
# GROCERY
# ═══════════════════════════════════════════════════════════════

class GroceryItemOut(BaseModel):
    name:               str
    total_quantity:     str
    category:           str
    estimated_cost_pkr: Optional[float] = None
    bulk_buy_tip:       Optional[str]   = None


class GroceryListOut(BaseModel):
    items:                    list[GroceryItemOut]
    total_items:              int
    estimated_total_cost_pkr: Optional[float] = None
    bulk_buy_savings:         Optional[str]   = None
    shopping_notes:           Optional[str]   = None
    by_category:              dict[str, list[GroceryItemOut]] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# PREP SCHEDULE
# ═══════════════════════════════════════════════════════════════

class PrepTaskOut(BaseModel):
    task:                str
    prep_day:            str
    duration_minutes:    int
    covers_meals:        list[str]
    storage_instruction: str
    reheating_tip:       Optional[str] = None


class PrepScheduleOut(BaseModel):
    tasks:               list[PrepTaskOut]
    total_prep_time_min: int
    prep_days:           list[str]
    efficiency_notes:    str


# ═══════════════════════════════════════════════════════════════
# MEAL PLAN
# ═══════════════════════════════════════════════════════════════

class MealSlotOut(BaseModel):
    slot:            str   # breakfast / lunch / dinner / snack
    dish_name:       str
    cuisine:         Optional[str]
    calories:        int
    protein_g:       float
    carbs_g:         float
    fat_g:           float
    fiber_g:         Optional[float] = None
    prep_time_minutes: Optional[int] = None


class DayPlanOut(BaseModel):
    day:             str
    meals:           list[MealSlotOut]
    total_calories:  int
    total_protein_g: float
    total_carbs_g:   float
    total_fat_g:     float
    total_fiber_g:   float


class WeeklySummaryOut(BaseModel):
    avg_daily_calories:      float
    avg_daily_protein_g:     float
    avg_daily_carbs_g:       float
    avg_daily_fat_g:         float
    avg_daily_fiber_g:       float
    total_weekly_calories:   int
    calorie_target_hit_days: int
    notes:                   str


class MealPlanResponse(BaseModel):
    plan_id:         str
    week_start:      str
    status:          str
    days:            list[DayPlanOut]
    weekly_summary:  WeeklySummaryOut
    calorie_target:  int
    macro_split:     dict
    grocery_list:    Optional[GroceryListOut]   = None
    prep_schedule:   Optional[PrepScheduleOut]  = None


class MealPlanSummary(BaseModel):
    """Compact version for list endpoints."""
    plan_id:                 str
    week_start:              str
    status:                  str
    avg_daily_calories:      float
    calorie_target_hit_days: int