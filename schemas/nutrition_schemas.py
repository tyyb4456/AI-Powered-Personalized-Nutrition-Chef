"""
schemas/nutrition_schemas.py

Structured Pydantic models for all LLM outputs.
These replace free-text parsing and ensure every agent works
with validated, typed data — not raw strings.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


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
                f"Macro percentages must sum to 100. Got: protein={protein}, carbs={carbs}, fat={fat} → total={total}"
            )
        return fat


# ─────────────────────────────────────────────
# 2. Nutrition Facts (parsed from LLM recipe output)
# ─────────────────────────────────────────────

class NutritionFacts(BaseModel):
    calories:    int   = Field(..., ge=0,  description="Total calories in kcal")
    protein_g:   float = Field(..., ge=0,  description="Protein in grams")
    carbs_g:     float = Field(..., ge=0,  description="Carbohydrates in grams")
    fat_g:       float = Field(..., ge=0,  description="Fat in grams")
    fiber_g:     Optional[float] = Field(default=None, ge=0, description="Dietary fiber in grams")
    sodium_mg:   Optional[float] = Field(default=None, ge=0, description="Sodium in milligrams")

    @field_validator("calories")
    @classmethod
    def calories_must_be_realistic(cls, v: int) -> int:
        if v < 50:
            raise ValueError(f"Calories too low to be a real meal: {v} kcal")
        if v > 5000:
            raise ValueError(f"Calories suspiciously high for a single meal: {v} kcal")
        return v


# ─────────────────────────────────────────────
# 3. Single Ingredient (structured, not free text)
# ─────────────────────────────────────────────

class Ingredient(BaseModel):
    name:     str  = Field(..., description="Ingredient name, e.g. 'chicken breast'")
    quantity: str  = Field(..., description="Amount with unit, e.g. '200g' or '1 cup'")


# ─────────────────────────────────────────────
# 4. Full Recipe (what the LLM must return — structured)
# ─────────────────────────────────────────────

class RecipeOutput(BaseModel):
    dish_name:   str             = Field(..., description="Creative but relevant dish name")
    ingredients: list[Ingredient] = Field(..., description="Full ingredient list with quantities")
    steps:       list[str]       = Field(..., description="Numbered preparation steps")
    nutrition:   NutritionFacts  = Field(..., description="Nutritional breakdown of the complete dish")
    cuisine:     Optional[str]   = Field(default=None, description="Cuisine type, e.g. Indian, Italian")
    prep_time_minutes: Optional[int] = Field(default=None, ge=1, description="Estimated preparation time")

    def ingredients_as_strings(self) -> list[str]:
        """Helper to get ingredients as plain strings for allergen checking etc."""
        return [f"{ing.quantity} {ing.name}" for ing in self.ingredients]


# ─────────────────────────────────────────────
# 5. Substitution Output
# ─────────────────────────────────────────────

class SubstitutionItem(BaseModel):
    original_ingredient:    str = Field(..., description="The ingredient that was replaced")
    substitute_ingredient:  str = Field(..., description="The safe replacement ingredient")
    reason:                 str = Field(..., description="Why this substitution was made")


class SubstitutionOutput(BaseModel):
    substitutions_made: bool                  = Field(..., description="True if any substitutions were needed")
    substitutions:      list[SubstitutionItem] = Field(default_factory=list)
    revised_recipe:     Optional[RecipeOutput] = Field(
        default=None,
        description="Full revised recipe. Required if substitutions_made is True."
    )


# ─────────────────────────────────────────────
# 6. Macro Adjustment Output
# ─────────────────────────────────────────────

class MacroAdjustmentOutput(BaseModel):
    adjusted_recipe: RecipeOutput = Field(..., description="Revised recipe with adjusted macros")
    adjustment_notes: str         = Field(..., description="Explanation of what was changed and why")


# ─────────────────────────────────────────────
# 7. Validation Result (internal, not LLM output)
# ─────────────────────────────────────────────

class ValidationResult(BaseModel):
    passed:           bool  = Field(..., description="True if recipe meets all nutrition targets")
    calorie_check:    bool  = Field(..., description="Calories within ±10% of target")
    protein_check:    bool  = Field(..., description="Protein ratio within ±5% of target")
    carbs_check:      bool  = Field(..., description="Carbs ratio within ±5% of target")
    fat_check:        bool  = Field(..., description="Fat ratio within ±5% of target")
    notes:            str   = Field(..., description="Human-readable summary of validation result")
    calorie_diff_pct: float = Field(..., description="% difference from calorie target")