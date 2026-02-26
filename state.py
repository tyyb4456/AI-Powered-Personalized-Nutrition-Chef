"""
state.py

Central state model for the LangGraph pipeline.

Phase 2 additions:
- medical_conditions: list of structured MedicalCondition
- age_profile: AgeProfile computed by health_agent (age flags)
- learned_preferences: structured LearnedPreferences (replaces raw dict)
- recipe_context: list of RAG examples injected into recipe prompt
- session_id: for future persistence layer
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from schemas.nutrition_schemas import (
    MacroSplit,
    RecipeOutput,
    SubstitutionOutput,
    MacroAdjustmentOutput,
    ValidationResult,
    MedicalCondition,
    AgeProfile,
    LearnedPreferences,
    RecipeContext,
)


class NutritionState(BaseModel):

    # ── Session ───────────────────────────────────────────────
    session_id: Optional[str] = None   # for future persistence

    # ── User Profile ──────────────────────────────────────────
    customer_id:    Optional[str]   = None
    name:           Optional[str]   = None
    age:            Optional[int]   = None
    gender:         Optional[str]   = None
    weight_kg:      Optional[float] = None
    height_cm:      Optional[float] = None
    activity_level: Optional[str]   = None
    allergies:      list[str]       = Field(default_factory=list)
    preferences:    Dict[str, Any]  = Field(default_factory=dict)
    fitness_goal:   Optional[str]   = None

    # [NEW] Medical conditions — influence macro targets and validation flags
    medical_conditions: list[MedicalCondition] = Field(default_factory=list)

    profile_collected: bool = False

    # ── Health Goal Agent outputs ─────────────────────────────
    calorie_target:   Optional[int]       = None
    macro_split:      Optional[MacroSplit] = None
    goal_type:        Optional[str]       = None   # canonical: muscle_gain / fat_loss / maintenance
    goal_interpreted: bool                = False

    # [NEW] Age-specific dietary flags computed by health_agent
    age_profile: Optional[AgeProfile] = None

    # ── RAG Context (few-shot recipe examples) ────────────────
    # [NEW] Injected into recipe prompt to ground the LLM
    recipe_context: list[RecipeContext] = Field(default_factory=list)

    # ── Recipe Agent outputs ──────────────────────────────────
    generated_recipe: Optional[RecipeOutput] = None
    recipe_generated: bool                   = False

    # ── Nutrition Validator outputs ───────────────────────────
    validation_result:  Optional[ValidationResult] = None
    validation_passed:  Optional[bool]             = None
    validation_notes:   Optional[str]              = None

    # ── Macro Adjustment Agent outputs ────────────────────────
    macro_adjustment_output: Optional[MacroAdjustmentOutput] = None
    adjusted_by_macro_agent: bool                            = False

    # ── Substitution Agent outputs ────────────────────────────
    substitution_output: Optional[SubstitutionOutput] = None
    substitutions_made:  bool                         = False

    # ── Final recipe ──────────────────────────────────────────
    final_recipe: Optional[RecipeOutput] = None

    # ── Explainability Agent ──────────────────────────────────
    recipe_explanation: Optional[str] = None

    # ── Feedback ──────────────────────────────────────────────
    feedback_rating:    Optional[int] = None
    feedback_comment:   Optional[str] = None
    feedback_collected: bool          = False

    # ── Learning Loop ─────────────────────────────────────────
    # [NEW] Structured instead of raw dict
    learned_preferences: Optional[LearnedPreferences] = None
    updated_goals:       Optional[str]                = None

    # ── Pipeline Control ──────────────────────────────────────
    retry_count:    int           = 0
    pipeline_error: Optional[str] = None