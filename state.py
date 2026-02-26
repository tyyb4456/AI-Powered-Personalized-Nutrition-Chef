"""
state.py

Central state model for the LangGraph pipeline.

Key rules:
- Every field has a sensible default so LangGraph can merge partial updates.
- Agents return ONLY the keys they changed — LangGraph merges the rest.
- All structured data uses schemas from schemas/nutrition_schemas.py,
  not raw dicts or free-text strings.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from schemas.nutrition_schemas import (
    MacroSplit,
    RecipeOutput,
    SubstitutionOutput,
    MacroAdjustmentOutput,
    ValidationResult,
)


class NutritionState(BaseModel):

    # ── User Profile ──────────────────────────────────────────
    customer_id:   Optional[str]  = None
    name:          Optional[str]  = None
    age:           Optional[int]  = None
    gender:        Optional[str]  = None          # needed for accurate BMR
    weight_kg:     Optional[float] = None          # needed for accurate BMR
    height_cm:     Optional[float] = None          # needed for accurate BMR
    activity_level: Optional[str] = None           # sedentary/light/moderate/active/very_active
    allergies:     list[str]      = Field(default_factory=list)
    preferences:   Dict[str, Any] = Field(default_factory=dict)
    fitness_goal:  Optional[str]  = None
    profile_collected: bool       = False

    # ── Health Goal Agent outputs ─────────────────────────────
    calorie_target:    Optional[int]       = None
    macro_split:       Optional[MacroSplit] = None
    goal_interpreted:  bool                = False

    # ── Recipe Agent outputs ──────────────────────────────────
    # Structured recipe — replaces generated_recipe (plain string)
    generated_recipe:  Optional[RecipeOutput] = None
    recipe_generated:  bool                   = False

    # ── Nutrition Validator outputs ───────────────────────────
    validation_result:  Optional[ValidationResult] = None
    # Convenience booleans (derived from validation_result, set by validator)
    validation_passed:  Optional[bool] = None
    validation_notes:   Optional[str]  = None

    # ── Macro Adjustment Agent outputs ────────────────────────
    macro_adjustment_output:  Optional[MacroAdjustmentOutput] = None
    adjusted_by_macro_agent:  bool = False

    # ── Substitution Agent outputs ────────────────────────────
    substitution_output:  Optional[SubstitutionOutput] = None
    substitutions_made:   bool = False

    # ── Final recipe (what gets shown to user) ────────────────
    # This is set at the END of the pipeline — either revised or original
    final_recipe: Optional[RecipeOutput] = None

    # ── Explainability Agent ──────────────────────────────────
    recipe_explanation: Optional[str] = None

    # ── Feedback ──────────────────────────────────────────────
    feedback_rating:   Optional[int] = None
    feedback_comment:  Optional[str] = None
    feedback_collected: bool         = False

    # ── Learning Loop ─────────────────────────────────────────
    learned_preferences: Dict[str, Any] = Field(default_factory=dict)
    updated_goals:       Optional[str]  = None

    # ── Pipeline Control ──────────────────────────────────────
    retry_count:    int           = 0      # tracks macro adjustment retries
    pipeline_error: Optional[str] = None  # set if an agent fails hard