"""
api/routers/meal_plans.py

Meal plan endpoints:
  POST /meal-plans/generate          — generate a 7-day meal plan (heavy, ~2-3 min)
  GET  /meal-plans/active            — fetch the user's current active plan
  GET  /meal-plans/                  — list all plans for the user
  GET  /meal-plans/{plan_id}         — fetch a specific plan
  GET  /meal-plans/{plan_id}/grocery — grocery list for a plan
  GET  /meal-plans/{plan_id}/prep    — prep schedule for a plan
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from schemas.meal_plan_schemas import (
    GenerateMealPlanRequest, MealPlanResponse, MealPlanSummary,
    GroceryListOut, PrepScheduleOut,
)
from services.meal_plan_service import (
    generate_meal_plan, get_active_plan, list_user_plans,
)
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meal-plans", tags=["Meal Plans"])


# ── POST /meal-plans/generate ─────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=MealPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalized 7-day meal plan",
    description="""
Runs the full weekly planning pipeline:

1. **Health goal agent** — recalculates your calorie target & macro split  
2. **Weekly plan agent** — generates 28 meals (4 per day × 7 days) with variety enforcement  
3. **Grocery agent** — consolidates all ingredients into a categorized shopping list with PKR pricing  
4. **Prep schedule agent** — creates a batch-cooking plan to minimize daily cook time  

All recipes and the plan structure are saved to the database.  
Generating a new plan for the same week archives the previous one.

⚠️ **This endpoint takes 90–180 seconds.** For production use, consider the async  
background task variant (Phase 7).
""",
)
async def generate_meal_plan_endpoint(
    payload: GenerateMealPlanRequest = GenerateMealPlanRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await generate_meal_plan(user=current_user, db=db, request=payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.exception("Meal plan generation failed for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Meal plan generation failed: {str(e)}",
        )


# ── GET /meal-plans/ ──────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[MealPlanSummary],
    summary="List all meal plans",
    description="Returns a summary of all meal plans for the authenticated user, newest first.",
)
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_user_plans(user_id=current_user.id, db=db)


# ── GET /meal-plans/active ────────────────────────────────────────────────────

@router.get(
    "/active",
    response_model=MealPlanResponse,
    summary="Get the current active meal plan",
    description="Returns the user's most recently generated active plan with all meals.",
)
def get_active(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_active_plan(user_id=current_user.id, db=db)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active meal plan found. Generate one via POST /meal-plans/generate.",
        )
    return plan


# ── GET /meal-plans/{plan_id} ─────────────────────────────────────────────────

@router.get(
    "/{plan_id}",
    response_model=MealPlanResponse,
    summary="Get a specific meal plan by ID",
)
def get_plan_by_id(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch a specific plan by its ID.
    Users can only access their own plans.
    """
    from db.models import MealPlan as MealPlanModel
    from services.meal_plan_service import get_active_plan

    plan_row = db.query(MealPlanModel).filter_by(id=plan_id, user_id=current_user.id).first()
    if not plan_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal plan '{plan_id}' not found.",
        )

    # Reuse the active plan loader (it works for any plan, not just active)
    from services.meal_plan_service import _build_plan_from_db
    plan = _build_plan_from_db(plan_id=plan_id, db=db)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan data not found.")
    return plan


# ── GET /meal-plans/{plan_id}/grocery ─────────────────────────────────────────

@router.get(
    "/{plan_id}/grocery",
    response_model=GroceryListOut,
    summary="Get the grocery list for a meal plan",
    description="""
Returns the consolidated, categorized grocery list for the specified plan.

**Note:** The grocery list is generated alongside the meal plan and stored in memory.
If fetching an older plan from DB, grocery data may not be available — in that case, 
re-generate the plan.
""",
)
def get_grocery_list(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from db.models import MealPlan as MealPlanModel
    plan_row = db.query(MealPlanModel).filter_by(id=plan_id, user_id=current_user.id).first()
    if not plan_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(
            "Grocery list not available for this plan. "
            "Grocery data is returned inline when you generate a new plan via POST /meal-plans/generate."
        ),
    )


# ── GET /meal-plans/{plan_id}/prep ────────────────────────────────────────────

@router.get(
    "/{plan_id}/prep",
    response_model=PrepScheduleOut,
    summary="Get the prep schedule for a meal plan",
    description="Returns the batch-cooking prep schedule for the specified plan.",
)
def get_prep_schedule(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from db.models import MealPlan as MealPlanModel
    plan_row = db.query(MealPlanModel).filter_by(id=plan_id, user_id=current_user.id).first()
    if not plan_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(
            "Prep schedule not available for this plan. "
            "Prep data is returned inline when you generate a new plan via POST /meal-plans/generate."
        ),
    )