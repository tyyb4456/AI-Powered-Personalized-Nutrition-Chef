"""
schemas/nutrition_schemas.py

Structured Pydantic models for all LLM outputs.
Phase 2 additions:
- MedicalCondition model
- AgeProfile with dietary flags
- LearnedPreferences for cross-session memory
- RecipeContext for RAG-style injection
- Extended NutritionFacts with micronutrients
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


# ─────────────────────────────────────────────
# 1. Macro Split
# ─────────────────────────────────────────────

class MacroSplit(BaseModel):
    protein: int = Field(..., ge=0, le=100, description="Protein percentage of total calories")
    carbs: int   = Field(..., ge=0, le=100, description="Carbohydrate percentage of total calories")
    fat: int     = Field(..., ge=0, le=100, description="Fat percentage of total calories")

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


# ─────────────────────────────────────────────
# 2. Nutrition Facts (extended with micronutrients)
# ─────────────────────────────────────────────

class NutritionFacts(BaseModel):
    calories:    int   = Field(..., ge=0,  description="Total calories in kcal")
    protein_g:   float = Field(..., ge=0,  description="Protein in grams")
    carbs_g:     float = Field(..., ge=0,  description="Carbohydrates in grams")
    fat_g:       float = Field(..., ge=0,  description="Fat in grams")
    fiber_g:     Optional[float] = Field(default=None, ge=0, description="Dietary fiber in grams")
    sodium_mg:   Optional[float] = Field(default=None, ge=0, description="Sodium in milligrams")
    calcium_mg:  Optional[float] = Field(default=None, ge=0, description="Calcium in milligrams")
    iron_mg:     Optional[float] = Field(default=None, ge=0, description="Iron in milligrams")
    sugar_g:     Optional[float] = Field(default=None, ge=0, description="Sugar in grams")

    @field_validator("calories")
    @classmethod
    def calories_must_be_realistic(cls, v: int) -> int:
        if v < 50:
            raise ValueError(f"Calories too low to be a real meal: {v} kcal")
        if v > 5000:
            raise ValueError(f"Calories suspiciously high for a single meal: {v} kcal")
        return v


# ─────────────────────────────────────────────
# 3. Single Ingredient
# ─────────────────────────────────────────────

class Ingredient(BaseModel):
    name:     str = Field(..., description="Ingredient name, e.g. 'chicken breast'")
    quantity: str = Field(..., description="Amount with unit, e.g. '200g' or '1 cup'")


# ─────────────────────────────────────────────
# 4. Full Recipe Output
# ─────────────────────────────────────────────

class RecipeOutput(BaseModel):
    dish_name:         str             = Field(..., description="Creative but relevant dish name")
    ingredients:       list[Ingredient] = Field(..., description="Full ingredient list with quantities")
    steps:             list[str]       = Field(..., description="Numbered preparation steps")
    nutrition:         NutritionFacts  = Field(..., description="Nutritional breakdown of the complete dish")
    cuisine:           Optional[str]   = Field(default=None, description="Cuisine type")
    prep_time_minutes: Optional[int]   = Field(default=None, ge=1, description="Estimated prep time")
    meal_type:         Optional[str]   = Field(default=None, description="breakfast / lunch / dinner / snack")

    def ingredients_as_strings(self) -> list[str]:
        return [f"{ing.quantity} {ing.name}" for ing in self.ingredients]


# ─────────────────────────────────────────────
# 5. Substitution Output
# ─────────────────────────────────────────────

class SubstitutionItem(BaseModel):
    original_ingredient:   str = Field(..., description="The ingredient that was replaced")
    substitute_ingredient: str = Field(..., description="The safe replacement ingredient")
    reason:                str = Field(..., description="Why this substitution was made")


class SubstitutionOutput(BaseModel):
    substitutions_made: bool                   = Field(..., description="True if any substitutions were needed")
    substitutions:      list[SubstitutionItem]  = Field(default_factory=list)
    revised_recipe:     Optional[RecipeOutput]  = Field(
        default=None,
        description="Full revised recipe. Required if substitutions_made is True."
    )


# ─────────────────────────────────────────────
# 6. Macro Adjustment Output
# ─────────────────────────────────────────────

class MacroAdjustmentOutput(BaseModel):
    adjusted_recipe:  RecipeOutput = Field(..., description="Revised recipe with adjusted macros")
    adjustment_notes: str          = Field(..., description="Explanation of what was changed and why")


# ─────────────────────────────────────────────
# 7. Validation Result
# ─────────────────────────────────────────────

class ValidationResult(BaseModel):
    passed:           bool  = Field(..., description="True if recipe meets all nutrition targets")
    calorie_check:    bool  = Field(..., description="Calories within ±10% of target")
    protein_check:    bool  = Field(..., description="Protein ratio within ±5% of target")
    carbs_check:      bool  = Field(..., description="Carbs ratio within ±5% of target")
    fat_check:        bool  = Field(..., description="Fat ratio within ±5% of target")
    fiber_check:      bool  = Field(default=True, description="Fiber meets minimum if specified")
    allergen_check:   bool  = Field(default=True, description="No allergens detected in final recipe")
    notes:            str   = Field(..., description="Human-readable summary of validation result")
    calorie_diff_pct: float = Field(..., description="% difference from calorie target")


# ─────────────────────────────────────────────
# 8. [NEW] Medical Condition
# ─────────────────────────────────────────────

MedicalConditionType = Literal[
    "diabetes",
    "hypertension",
    "celiac",
    "lactose_intolerance",
    "kidney_disease",
    "heart_disease",
    "ibs",
    "anemia",
    "osteoporosis",
    "none",
]

class MedicalCondition(BaseModel):
    condition: MedicalConditionType = Field(..., description="Type of medical condition")
    notes:     Optional[str]        = Field(default=None, description="Any extra detail from user")


# ─────────────────────────────────────────────
# 9. [NEW] Age-Specific Dietary Profile
# ─────────────────────────────────────────────

class AgeProfile(BaseModel):
    """
    Flags derived from age that influence recipe generation and validation.
    Computed once in health_agent and stored in state.
    """
    age_group:            str   = Field(..., description="teen / young_adult / adult / senior")
    higher_protein_need:  bool  = Field(default=False, description="True for seniors (muscle preservation)")
    lower_sodium_need:    bool  = Field(default=False, description="True for seniors / hypertension")
    higher_calcium_need:  bool  = Field(default=False, description="True for teens and seniors (bone health)")
    higher_iron_need:     bool  = Field(default=False, description="True for teens")
    lower_calorie_adjust: bool  = Field(default=False, description="True for seniors (lower TDEE)")
    notes:                str   = Field(default="", description="Human-readable summary of age flags")


# ─────────────────────────────────────────────
# 10. [NEW] Learned Preferences (cross-session memory)
# ─────────────────────────────────────────────

class LearnedPreferences(BaseModel):
    """
    Structured preferences the learning loop extracts from feedback.
    Stored per user and injected into future recipe prompts.
    """
    liked_ingredients:    list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    preferred_textures:   list[str] = Field(default_factory=list)   # e.g. "crispy", "soft"
    preferred_cuisines:   list[str] = Field(default_factory=list)
    avoided_cuisines:     list[str] = Field(default_factory=list)
    spice_preference:     Optional[str] = Field(default=None)       # low / medium / high
    goal_refinement:      Optional[str] = Field(default=None)       # updated goal interpretation
    session_insights:     list[str] = Field(default_factory=list)   # free-text notes from LLM


# ─────────────────────────────────────────────
# 11. [NEW] Recipe Context (RAG-style few-shot examples)
# ─────────────────────────────────────────────

class RecipeContext(BaseModel):
    """
    A lightweight recipe example injected into the recipe prompt
    to ground the LLM in realistic, cuisine-appropriate dishes.
    """
    dish_name:    str       = Field(..., description="Example dish name")
    cuisine:      str       = Field(..., description="Cuisine type")
    goal_fit:     str       = Field(..., description="Which goal this suits: muscle_gain / fat_loss / maintenance")
    key_proteins: list[str] = Field(..., description="Main protein sources in this dish")
    approx_calories: int    = Field(..., description="Approximate calories")
    notes:        str       = Field(default="", description="Why this is a good example")