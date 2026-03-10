"""
api/schemas/recipe_schemas.py

Request / response models for recipe endpoints.
"""

from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# REQUEST
# ═══════════════════════════════════════════════════════════════

class GenerateRecipeRequest(BaseModel):
    """
    All fields are optional — missing values are loaded from the user's
    saved profile in the DB. Providing them here overrides the profile
    just for this request (useful for one-off experiments).
    """
    # Override profile fields for this request only
    fitness_goal:   Optional[str]   = Field(default=None, examples=["fat_loss", "muscle_gain", "maintenance"])
    cuisine:        Optional[str]   = Field(default=None, examples=["pakistani", "italian", "chinese"])
    spice_level:    Optional[str]   = Field(default=None, examples=["mild", "medium", "hot"])
    meal_type:      Optional[str]   = Field(default=None, examples=["breakfast", "lunch", "dinner", "snack"])

    # Optional extra allergies for this request (merged with profile allergies)
    extra_allergies: list[str]      = Field(default_factory=list, examples=[["shellfish"]])

class FollowupRequest(BaseModel):
    """Body for POST /recipes/{recipe_id}/followup"""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        examples=[
            "How much protein does this have?",
            "Can you make it vegan?",
            "What can I substitute for the chicken?",
            "Reduce the calories by 200 kcal",
        ],
        description=(
            "A follow-up question or modification request about the generated recipe. "
            "The AI will automatically decide whether to answer your question or "
            "regenerate the recipe based on your input."
        ),
    )


# ═══════════════════════════════════════════════════════════════
# RESPONSE BUILDING BLOCKS
# ═══════════════════════════════════════════════════════════════

class IngredientOut(BaseModel):
    name:     str
    quantity: str


class NutritionOut(BaseModel):
    calories:   int
    protein_g:  float
    carbs_g:    float
    fat_g:      float
    fiber_g:    Optional[float] = None
    sodium_mg:  Optional[float] = None
    calcium_mg: Optional[float] = None
    iron_mg:    Optional[float] = None
    sugar_g:    Optional[float] = None


class SubstitutionOut(BaseModel):
    original:   str
    substitute: str
    reason:     str


class ValidationOut(BaseModel):
    passed:           bool
    calorie_check:    bool
    protein_check:    bool
    carbs_check:      bool
    fat_check:        bool
    fiber_check:      bool
    allergen_check:   bool
    calorie_diff_pct: float
    notes:            str


# ═══════════════════════════════════════════════════════════════
# MAIN RESPONSE
# ═══════════════════════════════════════════════════════════════

class RecipeResponse(BaseModel):
    recipe_id:         str
    dish_name:         str
    cuisine:           Optional[str]
    meal_type:         Optional[str]
    prep_time_minutes: Optional[int]
    ingredients:       list[IngredientOut]
    steps:             list[str]
    nutrition:         NutritionOut
    substitutions:     list[SubstitutionOut]
    explanation:       Optional[str]
    validation:        ValidationOut
    calorie_target:    int
    macro_split:       dict    # {"protein": 35, "carbs": 40, "fat": 25}
    from_cache:        bool = False


class RecipeSummary(BaseModel):
    """Compact version for list endpoints."""
    recipe_id:  str
    dish_name:  str
    cuisine:    Optional[str]
    meal_type:  Optional[str]
    calories:   int
    protein_g:  float
    carbs_g:    float
    fat_g:      float


class RecipeListResponse(BaseModel):
    recipes: list[RecipeSummary]
    total:   int
    page:    int
    limit:   int

# ═══════════════════════════════════════════════════════════════
# FOLLOW-UP RESPONSE  ← Phase 8
# ═══════════════════════════════════════════════════════════════

class FollowupResponse(BaseModel):
    """
    Unified response for POST /recipes/{recipe_id}/followup

    intent == "question":
      - answer is populated with the AI's answer
      - recipe is None

    intent == "modify":
      - recipe is populated with the fully regenerated RecipeResponse
      - answer is None

    intent == "done":
      - answer is a short farewell message
      - recipe is None

    followup_history contains the full Q&A log for this session,
    which the client should persist and pass back if implementing
    a stateful multi-turn session (optional).
    """
    intent:           Literal["question", "modify", "done"]
    answer:           Optional[str]           = Field(
        default=None,
        description="Populated when intent is 'question' or 'done'.",
    )
    recipe:           Optional[RecipeResponse] = Field(
        default=None,
        description="Populated when intent is 'modify' — the regenerated recipe.",
    )
    followup_history: list[str] = Field(
        default_factory=list,
        description="Running log of all follow-up turns in this session.",
    )