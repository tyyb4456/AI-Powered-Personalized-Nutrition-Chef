"""
schemas/nutrition_schemas.py

All Pydantic models for the Nutrition AI system.

Phase 1: Core recipe + validation models
Phase 2: MedicalCondition, AgeProfile, LearnedPreferences, RecipeContext
Phase 3: MealPlan, WeeklyNutrition, GroceryList, MealPrepSchedule,
         ProgressLog, FoodImageAnalysis
"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import date


# ═══════════════════════════════════════════════════════════════
# PHASE 1 — Core Models
# ═══════════════════════════════════════════════════════════════

class MacroSplit(BaseModel):
    protein: int = Field(..., ge=0, le=100)
    carbs:   int = Field(..., ge=0, le=100)
    fat:     int = Field(..., ge=0, le=100)

    @field_validator("fat")
    @classmethod
    def macros_must_sum_to_100(cls, fat: int, info) -> int:
        protein = info.data.get("protein", 0)
        carbs   = info.data.get("carbs", 0)
        total   = protein + carbs + fat
        if total != 100:
            raise ValueError(
                f"Macro percentages must sum to 100. "
                f"Got: protein={protein}, carbs={carbs}, fat={fat} → total={total}"
            )
        return fat


class NutritionFacts(BaseModel):
    calories:   int            = Field(..., ge=0)
    protein_g:  float          = Field(..., ge=0)
    carbs_g:    float          = Field(..., ge=0)
    fat_g:      float          = Field(..., ge=0)
    fiber_g:    Optional[float] = Field(default=None, ge=0)
    sodium_mg:  Optional[float] = Field(default=None, ge=0)
    calcium_mg: Optional[float] = Field(default=None, ge=0)
    iron_mg:    Optional[float] = Field(default=None, ge=0)
    sugar_g:    Optional[float] = Field(default=None, ge=0)

    @field_validator("calories")
    @classmethod
    def calories_must_be_realistic(cls, v: int) -> int:
        if v < 50:
            raise ValueError(f"Calories too low: {v} kcal")
        if v > 5000:
            raise ValueError(f"Calories too high: {v} kcal")
        return v


class Ingredient(BaseModel):
    name:     str = Field(..., description="Ingredient name")
    quantity: str = Field(..., description="Amount with unit e.g. '200g'")


class RecipeOutput(BaseModel):
    dish_name:         str              = Field(...)
    ingredients:       list[Ingredient] = Field(...)
    steps:             list[str]        = Field(...)
    nutrition:         NutritionFacts   = Field(...)
    cuisine:           Optional[str]    = None
    prep_time_minutes: Optional[int]    = Field(default=None, ge=1)
    meal_type:         Optional[str]    = Field(
        default=None,
        description="breakfast / lunch / dinner / snack"
    )

    def ingredients_as_strings(self) -> list[str]:
        return [f"{ing.quantity} {ing.name}" for ing in self.ingredients]


class SubstitutionItem(BaseModel):
    original_ingredient:   str = Field(...)
    substitute_ingredient: str = Field(...)
    reason:                str = Field(...)


class SubstitutionOutput(BaseModel):
    substitutions_made: bool                  = Field(...)
    substitutions:      list[SubstitutionItem] = Field(default_factory=list)
    revised_recipe:     Optional[RecipeOutput] = None


class MacroAdjustmentOutput(BaseModel):
    adjusted_recipe:  RecipeOutput = Field(...)
    adjustment_notes: str          = Field(...)


class ValidationResult(BaseModel):
    passed:           bool  = Field(...)
    calorie_check:    bool  = Field(...)
    protein_check:    bool  = Field(...)
    carbs_check:      bool  = Field(...)
    fat_check:        bool  = Field(...)
    fiber_check:      bool  = Field(default=True)
    allergen_check:   bool  = Field(default=True)
    notes:            str   = Field(...)
    calorie_diff_pct: float = Field(...)


# ═══════════════════════════════════════════════════════════════
# PHASE 2 — Intelligence Models
# ═══════════════════════════════════════════════════════════════

MedicalConditionType = Literal[
    "diabetes", "hypertension", "celiac", "lactose_intolerance",
    "kidney_disease", "heart_disease", "ibs", "anemia", "osteoporosis", "none",
]


class MedicalCondition(BaseModel):
    condition: MedicalConditionType = Field(...)
    notes:     Optional[str]        = None


class AgeProfile(BaseModel):
    age_group:            str  = Field(...)
    higher_protein_need:  bool = False
    lower_sodium_need:    bool = False
    higher_calcium_need:  bool = False
    higher_iron_need:     bool = False
    lower_calorie_adjust: bool = False
    notes:                str  = ""


class LearnedPreferences(BaseModel):
    liked_ingredients:    list[str]    = Field(default_factory=list)
    disliked_ingredients: list[str]    = Field(default_factory=list)
    preferred_textures:   list[str]    = Field(default_factory=list)
    preferred_cuisines:   list[str]    = Field(default_factory=list)
    avoided_cuisines:     list[str]    = Field(default_factory=list)
    spice_preference:     Optional[str] = None
    goal_refinement:      Optional[str] = None
    session_insights:     list[str]    = Field(default_factory=list)


class RecipeContext(BaseModel):
    dish_name:       str       = Field(...)
    cuisine:         str       = Field(...)
    goal_fit:        str       = Field(...)
    key_proteins:    list[str] = Field(...)
    approx_calories: int       = Field(...)
    notes:           str       = ""


# ═══════════════════════════════════════════════════════════════
# PHASE 3 — New Agent Models
# ═══════════════════════════════════════════════════════════════

# ── 3.1 Meal Plan ─────────────────────────────────────────────

MealSlotType = Literal["breakfast", "lunch", "dinner", "snack"]
DayOfWeek    = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class MealSlot(BaseModel):
    """A single meal within a day."""
    slot:             MealSlotType    = Field(...)
    recipe:           RecipeOutput    = Field(...)
    target_calories:  int             = Field(..., ge=0)


class DayPlan(BaseModel):
    """All meals for one day of the week."""
    day:        DayOfWeek       = Field(...)
    meals:      list[MealSlot]  = Field(...)
    total_calories:  int        = Field(..., ge=0)
    total_protein_g: float      = Field(..., ge=0)
    total_carbs_g:   float      = Field(..., ge=0)
    total_fat_g:     float      = Field(..., ge=0)
    total_fiber_g:   float      = Field(default=0.0, ge=0)


class WeeklyNutritionSummary(BaseModel):
    """Aggregated nutrition across all 7 days."""
    avg_daily_calories:  float = Field(...)
    avg_daily_protein_g: float = Field(...)
    avg_daily_carbs_g:   float = Field(...)
    avg_daily_fat_g:     float = Field(...)
    avg_daily_fiber_g:   float = Field(default=0.0)
    total_weekly_calories: int = Field(...)
    calorie_target_hit_days: int = Field(..., description="Days within ±10% of target")
    notes:               str  = Field(default="")


class MealPlan(BaseModel):
    """Full 7-day meal plan."""
    days:              list[DayPlan]            = Field(...)
    weekly_summary:    WeeklyNutritionSummary   = Field(...)
    plan_generated_at: Optional[str]            = None   # ISO timestamp


# ── 3.2 Grocery List ──────────────────────────────────────────

class GroceryItem(BaseModel):
    name:              str            = Field(...)
    total_quantity:    str            = Field(..., description="Consolidated quantity e.g. '1.4kg'")
    category:          str            = Field(..., description="produce / protein / dairy / pantry / spices / frozen")
    estimated_cost_pkr: Optional[float] = Field(default=None, ge=0)
    bulk_buy_tip:      Optional[str]  = None


class GroceryList(BaseModel):
    items:             list[GroceryItem] = Field(...)
    total_items:       int               = Field(...)
    estimated_total_cost_pkr: Optional[float] = None
    bulk_buy_savings:  Optional[str]     = None
    shopping_notes:    Optional[str]     = None

    def by_category(self) -> dict[str, list[GroceryItem]]:
        """Group items by category for display."""
        result: dict[str, list[GroceryItem]] = {}
        for item in self.items:
            result.setdefault(item.category, []).append(item)
        return result


# ── 3.3 Meal Prep Schedule ────────────────────────────────────

class PrepTask(BaseModel):
    """A single batch-cooking task."""
    task:              str           = Field(..., description="e.g. 'Cook 2kg brown rice'")
    prep_day:          str           = Field(..., description="e.g. 'Sunday' or 'Wednesday'")
    duration_minutes:  int           = Field(..., ge=1)
    covers_meals:      list[str]     = Field(..., description="Dish names this prep covers")
    storage_instruction: str         = Field(..., description="e.g. 'Refrigerate in airtight container, use within 4 days'")
    reheating_tip:     Optional[str] = None


class MealPrepSchedule(BaseModel):
    tasks:               list[PrepTask] = Field(...)
    total_prep_time_min: int            = Field(..., ge=0)
    prep_days:           list[str]      = Field(..., description="Which days require prep")
    efficiency_notes:    str            = Field(default="")


# ── 3.4 Progress Tracking ─────────────────────────────────────

class MealLogEntry(BaseModel):
    """One logged meal (consumed vs planned)."""
    log_date:        str            = Field(..., description="ISO date e.g. '2025-03-01'")
    meal_slot:       MealSlotType   = Field(...)
    dish_name:       str            = Field(...)
    planned:         bool           = Field(..., description="Was this a planned meal?")
    calories:        int            = Field(..., ge=0)
    protein_g:       float          = Field(..., ge=0)
    carbs_g:         float          = Field(..., ge=0)
    fat_g:           float          = Field(..., ge=0)
    source:          str            = Field(default="manual", description="manual / image / plan")


class DailyAdherence(BaseModel):
    """Adherence summary for one day."""
    log_date:          str   = Field(...)
    planned_calories:  int   = Field(...)
    actual_calories:   int   = Field(...)
    adherence_pct:     float = Field(...)
    meals_logged:      int   = Field(...)
    meals_skipped:     int   = Field(...)


class WeeklyProgressReport(BaseModel):
    """LLM-generated progress analysis."""
    week_start:          str        = Field(...)
    week_end:            str        = Field(...)
    avg_adherence_pct:   float      = Field(...)
    best_day:            str        = Field(...)
    worst_day:           str        = Field(...)
    patterns_identified: list[str]  = Field(default_factory=list)
    recommendations:     list[str]  = Field(default_factory=list)
    goal_progress:       str        = Field(...)
    motivational_note:   str        = Field(default="")


# ── 3.5 Food Image Analysis ───────────────────────────────────

class IdentifiedFoodItem(BaseModel):
    """One food item detected in the image."""
    name:            str            = Field(...)
    estimated_amount: str           = Field(..., description="e.g. '1 cup' or '150g'")
    confidence:      str            = Field(..., description="high / medium / low")


class FoodImageAnalysis(BaseModel):
    """Full result from the vision LLM."""
    identified_items:   list[IdentifiedFoodItem] = Field(...)
    estimated_nutrition: NutritionFacts           = Field(...)
    meal_type_guess:    Optional[MealSlotType]    = None
    analysis_notes:     str                       = Field(default="")
    confidence_overall: str                       = Field(..., description="high / medium / low")