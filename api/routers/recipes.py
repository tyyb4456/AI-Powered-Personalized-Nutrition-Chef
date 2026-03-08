"""
api/routers/recipes.py

Recipe endpoints:
  POST /recipes/generate          — generate a personalized recipe (LLM pipeline)
  GET  /recipes/{recipe_id}       — fetch a single saved recipe
  GET  /recipes/                  — list the authenticated user's past recipes
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from schemas.recipe_schemas import (
    GenerateRecipeRequest, RecipeResponse, RecipeSummary, RecipeListResponse,
)
from services.recipe_service import (
    generate_recipe, get_recipe_by_id, list_user_recipes,
)
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["Recipes"])


# ── POST /recipes/generate ────────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalized recipe",
    description="""
Runs the full AI pipeline:

1. **Health goal agent** — calculates your calorie target and macro split  
   from your saved profile (age, weight, height, activity level, goal).
2. **Recipe generator** — calls Gemini 2.5 Flash with your profile, 
   allergen constraints, and RAG-retrieved recipe examples.
3. **Nutrition validator** — checks calories ±10% and macros ±5%.
4. **Macro adjustment** — auto-corrects the recipe if validation fails (up to 2 retries).
5. **Substitution agent** — replaces any allergen-containing ingredients.
6. **Explainability agent** — explains *why* this recipe was chosen for you.

All fields in the request body are optional — missing values are loaded  
from your saved profile. Use them to override for a one-off request.

⏱️ Typical response time: 8–20 seconds (LLM calls).
""",
)
async def generate_recipe_endpoint(
    payload: GenerateRecipeRequest = GenerateRecipeRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a personalized, AI-crafted recipe.

    Requires a saved profile (set via `PUT /users/me`).  
    At minimum: `age`, `weight_kg`, `height_cm`, `fitness_goal` should be set.
    """
    try:
        return await generate_recipe(user=current_user, db=db, request=payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.exception("Recipe generation failed for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recipe generation failed: {str(e)}",
        )


# ── GET /recipes/ ─────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=RecipeListResponse,
    summary="List past recipes",
    description="Returns recipes previously generated for the authenticated user, newest first.",
)
def list_recipes(
    page:  int = Query(default=1,  ge=1,  description="Page number"),
    limit: int = Query(default=10, ge=1, le=50, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_user_recipes(user_id=current_user.id, db=db, page=page, limit=limit)


# ── GET /recipes/{recipe_id} ──────────────────────────────────────────────────

@router.get(
    "/{recipe_id}",
    response_model=RecipeResponse,   # ← was RecipeSummary
    summary="Get a recipe by ID",
)
def get_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch a saved recipe by its ID.

    Returns a compact summary. For the full recipe with steps and explanation,
    use the generate endpoint and store the response client-side.
    """
    recipe = get_recipe_by_id(recipe_id=recipe_id, db=db)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe '{recipe_id}' not found.",
        )
    return recipe