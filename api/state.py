"""
state.py — Phase 8 (Follow-up)

Phase 8 additions:
  - followup_prompt       : the user's follow-up message after recipe generation
  - followup_intent       : classified intent — "question" | "modify" | "done"
  - followup_answer       : the answer when intent == "question"
  - followup_modification : the regeneration instruction when intent == "modify"
  - followup_history      : running list of Q&A turns in this session
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
    current_recipe_id: Optional[str]          = None   # DB id of generated recipe

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

    # ── Follow-up (Phase 8) ───────────────────────────────────
    followup_prompt:       Optional[str]       = None  # user's follow-up message
    followup_intent:       Optional[str]       = None  # "question" | "modify" | "done"
    followup_answer:       Optional[str]       = None  # populated for "question" intent
    followup_modification: Optional[str]       = None  # regeneration instruction for "modify" intent
    followup_history:      list[str]           = Field(default_factory=list)  # running Q&A log

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
    retry_count: int  = 0
    error:       Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# WEEKLY PLAN STATE (unchanged)
# ═══════════════════════════════════════════════════════════════

class WeeklyPlanState(BaseModel):
    """Separate state for the weekly meal plan pipeline."""
    customer_id:    Optional[str]          = None
    name:           Optional[str]          = None
    age:            Optional[int]          = None
    gender:         Optional[str]          = None
    weight_kg:      Optional[float]        = None
    height_cm:      Optional[float]        = None
    activity_level: Optional[str]          = None
    allergies:      list[str]              = Field(default_factory=list)
    preferences:    Dict[str, Any]         = Field(default_factory=dict)
    fitness_goal:   Optional[str]          = None
    medical_conditions: list[MedicalCondition] = Field(default_factory=list)
    profile_collected:  bool               = False

    calorie_target: Optional[int]          = None
    macro_split:    Optional[MacroSplit]   = None
    goal_type:      Optional[str]          = None
    age_profile:    Optional[AgeProfile]   = None

    meal_plan:           Optional[MealPlan]          = None
    grocery_list:        Optional[GroceryList]       = None
    meal_prep_schedule:  Optional[MealPrepSchedule]  = None

    error: Optional[str] = None