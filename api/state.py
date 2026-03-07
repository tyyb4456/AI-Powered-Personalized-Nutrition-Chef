"""
state.py — Phase 4

Phase 4 addition:
- current_recipe_id: set by recipe_agent after saving to DB,
  consumed by feedback_agent to link feedback to the correct recipe row
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from schemas.nutrition_schemas import (
    MacroSplit, RecipeOutput, SubstitutionOutput,
    MacroAdjustmentOutput, ValidationResult,
    MedicalCondition, AgeProfile, LearnedPreferences, RecipeContext,
    MealPlan, GroceryList, MealPrepSchedule,
    MealLogEntry, WeeklyProgressReport, FoodImageAnalysis,
)


class NutritionState(BaseModel):

    # ── Session ────────────────────────────────────────────────
    session_id:  Optional[str] = None
    customer_id: Optional[str] = None   # DB primary key, set by profile_agent

    # ── User Profile ──────────────────────────────────────────
    name:           Optional[str]   = None
    age:            Optional[int]   = None
    gender:         Optional[str]   = None
    weight_kg:      Optional[float] = None
    height_cm:      Optional[float] = None
    activity_level: Optional[str]   = None
    allergies:      list[str]               = Field(default_factory=list)
    preferences:    Dict[str, Any]          = Field(default_factory=dict)
    fitness_goal:   Optional[str]           = None
    medical_conditions: list[MedicalCondition] = Field(default_factory=list)
    profile_collected:  bool                   = False

    # ── Health Goal Agent ─────────────────────────────────────
    calorie_target:   Optional[int]        = None
    macro_split:      Optional[MacroSplit] = None
    goal_type:        Optional[str]        = None
    goal_interpreted: bool                 = False
    age_profile:      Optional[AgeProfile] = None

    # ── RAG Context ───────────────────────────────────────────
    recipe_context: list[RecipeContext] = Field(default_factory=list)

    # ── Recipe Agent ──────────────────────────────────────────
    generated_recipe:  Optional[RecipeOutput] = None
    recipe_generated:  bool                   = False
    current_recipe_id: Optional[str]          = None   # [NEW] DB id of generated recipe

    # ── Validation ────────────────────────────────────────────
    validation_result: Optional[ValidationResult] = None
    validation_passed: Optional[bool]             = None
    validation_notes:  Optional[str]              = None

    # ── Macro Adjustment ──────────────────────────────────────
    macro_adjustment_output: Optional[MacroAdjustmentOutput] = None
    adjusted_by_macro_agent: bool                            = False

    # ── Substitution ──────────────────────────────────────────
    substitution_output: Optional[SubstitutionOutput] = None
    substitutions_made:  bool                         = False

    # ── Final Recipe ──────────────────────────────────────────
    final_recipe: Optional[RecipeOutput] = None

    # ── Explainability ────────────────────────────────────────
    recipe_explanation: Optional[str] = None

    # ── Feedback ──────────────────────────────────────────────
    feedback_rating:    Optional[int] = None
    feedback_comment:   Optional[str] = None
    feedback_collected: bool          = False

    # ── Learning ──────────────────────────────────────────────
    learned_preferences: Optional[LearnedPreferences] = None
    updated_goals:       Optional[str]                = None

    # ── Image Analysis ────────────────────────────────────────
    image_path:        Optional[str]               = None
    image_analysis:    Optional[FoodImageAnalysis]  = None
    pending_log_entry: Optional[MealLogEntry]       = None

    # ── Pipeline Control ──────────────────────────────────────
    retry_count:    int           = 0
    pipeline_error: Optional[str] = None


class WeeklyPlanState(BaseModel):

    # ── User profile ──────────────────────────────────────────
    name:               Optional[str]           = None
    age:                Optional[int]           = None
    gender:             Optional[str]           = None
    weight_kg:          Optional[float]         = None
    height_cm:          Optional[float]         = None
    activity_level:     Optional[str]           = None
    allergies:          list[str]               = Field(default_factory=list)
    preferences:        Dict[str, Any]          = Field(default_factory=dict)
    fitness_goal:       Optional[str]           = None
    medical_conditions: list[MedicalCondition]  = Field(default_factory=list)
    calorie_target:     Optional[int]           = None
    macro_split:        Optional[MacroSplit]    = None
    goal_type:          Optional[str]           = None
    age_profile:        Optional[AgeProfile]    = None
    learned_preferences: Optional[LearnedPreferences] = None

    # ── Meal Plan Agent ───────────────────────────────────────
    meal_plan:         Optional[MealPlan]  = None
    plan_generated:    bool               = False

    # ── Grocery Agent ─────────────────────────────────────────
    grocery_list:      Optional[GroceryList] = None
    grocery_generated: bool                  = False

    # ── Meal Prep Agent ───────────────────────────────────────
    prep_schedule:     Optional[MealPrepSchedule] = None
    prep_generated:    bool                       = False

    # ── Progress Agent ────────────────────────────────────────
    progress_report:    Optional[WeeklyProgressReport] = None
    progress_generated: bool                           = False

    # ── Pipeline control ──────────────────────────────────────
    pipeline_error: Optional[str] = None