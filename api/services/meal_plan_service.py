"""
api/services/meal_plan_service.py

Business logic for the weekly meal plan pipeline.

Pipeline (direct agent calls, no interrupts):
  health_goal_agent_node   → calorie target + macro split
  weekly_plan_agent_node   → 7 × 4 = 28 LLM calls (one per meal slot)
  grocery_agent_node       → consolidated grocery list
  meal_prep_agent_node     → batch-cooking prep schedule

⏱️ Typical time: 90–180 seconds (28 LLM calls for meal slots + 2 more for grocery/prep)

The pipeline is run in a ThreadPoolExecutor so FastAPI's event loop is not blocked.
All generated recipes are saved individually to the `recipes` table.
The meal plan header and items are saved to `meal_plans` / `meal_plan_items`.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from state import WeeklyPlanState
from db.models import User
from db.repositories import UserRepository, RecipeRepository, MealPlanRepository
from agents.health_agent        import health_goal_agent_node
from agents.weekly_plan_agent   import weekly_plan_agent_node
from agents.grocery_agent       import grocery_agent_node
from agents.meal_prep_agent     import meal_prep_agent_node
from schemas.meal_plan_schemas import (
    GenerateMealPlanRequest, MealPlanResponse, MealPlanSummary,
    DayPlanOut, MealSlotOut, WeeklySummaryOut,
    GroceryListOut, GroceryItemOut,
    PrepScheduleOut, PrepTaskOut,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)   # weekly plan is heavy — limit concurrency


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _next_monday() -> date:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7
    return today + timedelta(days=days_ahead or 7)


def _parse_week_start(raw: Optional[str]) -> date:
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return _next_monday()


# ═══════════════════════════════════════════════════════════════
# STATE BUILDER
# ═══════════════════════════════════════════════════════════════

def _build_weekly_state(
    user: User,
    db: Session,
    request: GenerateMealPlanRequest,
) -> WeeklyPlanState:
    """Load user profile from DB and populate WeeklyPlanState."""
    from db.models import UserProfile

    repo    = UserRepository(db)
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    prefs   = repo.get_preferences(user.id)
    allergies  = repo.get_allergies(user.id)
    conditions = repo.get_medical_conditions(user.id)

    all_allergies = list(set(allergies + request.extra_allergies))
    cuisine      = request.cuisine      or prefs.get("cuisine",     "any")
    spice_level  = request.spice_level  or prefs.get("spice_level", "medium")
    fitness_goal = request.fitness_goal or prefs.get("fitness_goal", "maintenance")

    return WeeklyPlanState(
        name           = user.name,
        age            = profile.age            if profile else None,
        gender         = profile.gender         if profile else None,
        weight_kg      = profile.weight_kg      if profile else None,
        height_cm      = profile.height_cm      if profile else None,
        activity_level = profile.activity_level if profile else "moderate",
        fitness_goal   = fitness_goal,
        allergies      = all_allergies,
        medical_conditions = conditions,
        preferences    = {"cuisine": cuisine, "spice_level": spice_level},
    )


# ═══════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════

def _run_weekly_pipeline(state: WeeklyPlanState) -> WeeklyPlanState:
    """Runs all 4 agents sequentially (blocking — called from thread pool)."""

    # Step 1: Calculate calorie target + macro split
    updates = health_goal_agent_node(state)
    state   = state.model_copy(update=updates)

    # Step 2: Generate 7-day meal plan (28 LLM calls)
    updates = weekly_plan_agent_node(state)
    state   = state.model_copy(update=updates)

    if state.pipeline_error or not state.meal_plan:
        raise ValueError(state.pipeline_error or "Meal plan generation failed.")

    # Step 3: Grocery list
    updates = grocery_agent_node(state)
    state   = state.model_copy(update=updates)

    # Step 4: Prep schedule
    updates = meal_prep_agent_node(state)
    state   = state.model_copy(update=updates)

    return state


# ═══════════════════════════════════════════════════════════════
# DB PERSISTENCE
# ═══════════════════════════════════════════════════════════════

def _persist_plan(
    user_id: str,
    state: WeeklyPlanState,
    week_start: date,
    db: Session,
) -> str:
    """
    Save all generated recipes and meal plan structure to the DB.
    Returns the plan_id.
    """
    recipe_repo = RecipeRepository(db)
    plan_repo   = MealPlanRepository(db)

    plan_id = plan_repo.create_plan(user_id=user_id, week_start=week_start)

    for day_plan in state.meal_plan.days:
        for meal_slot in day_plan.meals:
            recipe_id = recipe_repo.save(meal_slot.recipe, source="generated")
            plan_repo.add_item(
                plan_id=plan_id,
                recipe_id=recipe_id,
                day_of_week=day_plan.day,
                meal_slot=meal_slot.slot,
            )

    db.flush()
    logger.info("Meal plan %s persisted for user %s (%s)", plan_id, user_id, week_start)
    return plan_id


# ═══════════════════════════════════════════════════════════════
# RESPONSE BUILDERS
# ═══════════════════════════════════════════════════════════════

def _build_grocery_out(grocery) -> Optional[GroceryListOut]:
    if not grocery:
        return None
    items = [
        GroceryItemOut(
            name=i.name,
            total_quantity=i.total_quantity,
            category=i.category,
            estimated_cost_pkr=i.estimated_cost_pkr,
            bulk_buy_tip=i.bulk_buy_tip,
        )
        for i in grocery.items
    ]
    by_cat: dict[str, list[GroceryItemOut]] = {}
    for item in items:
        by_cat.setdefault(item.category, []).append(item)

    return GroceryListOut(
        items=items,
        total_items=grocery.total_items,
        estimated_total_cost_pkr=grocery.estimated_total_cost_pkr,
        bulk_buy_savings=grocery.bulk_buy_savings,
        shopping_notes=grocery.shopping_notes,
        by_category=by_cat,
    )


def _build_prep_out(prep) -> Optional[PrepScheduleOut]:
    if not prep:
        return None
    return PrepScheduleOut(
        tasks=[
            PrepTaskOut(
                task=t.task,
                prep_day=t.prep_day,
                duration_minutes=t.duration_minutes,
                covers_meals=t.covers_meals,
                storage_instruction=t.storage_instruction,
                reheating_tip=t.reheating_tip,
            )
            for t in prep.tasks
        ],
        total_prep_time_min=prep.total_prep_time_min,
        prep_days=prep.prep_days,
        efficiency_notes=prep.efficiency_notes,
    )


def _build_plan_response(
    plan_id: str,
    week_start: date,
    state: WeeklyPlanState,
) -> MealPlanResponse:
    mp  = state.meal_plan
    mac = state.macro_split

    days_out = []
    for dp in mp.days:
        meals_out = [
            MealSlotOut(
                slot=ms.slot,
                dish_name=ms.recipe.dish_name,
                cuisine=ms.recipe.cuisine,
                calories=ms.recipe.nutrition.calories,
                protein_g=ms.recipe.nutrition.protein_g,
                carbs_g=ms.recipe.nutrition.carbs_g,
                fat_g=ms.recipe.nutrition.fat_g,
                fiber_g=ms.recipe.nutrition.fiber_g,
                prep_time_minutes=ms.recipe.prep_time_minutes,
            )
            for ms in dp.meals
        ]
        days_out.append(DayPlanOut(
            day=dp.day,
            meals=meals_out,
            total_calories=dp.total_calories,
            total_protein_g=dp.total_protein_g,
            total_carbs_g=dp.total_carbs_g,
            total_fat_g=dp.total_fat_g,
            total_fiber_g=dp.total_fiber_g,
        ))

    summary = WeeklySummaryOut(
        avg_daily_calories=mp.weekly_summary.avg_daily_calories,
        avg_daily_protein_g=mp.weekly_summary.avg_daily_protein_g,
        avg_daily_carbs_g=mp.weekly_summary.avg_daily_carbs_g,
        avg_daily_fat_g=mp.weekly_summary.avg_daily_fat_g,
        avg_daily_fiber_g=mp.weekly_summary.avg_daily_fiber_g,
        total_weekly_calories=mp.weekly_summary.total_weekly_calories,
        calorie_target_hit_days=mp.weekly_summary.calorie_target_hit_days,
        notes=mp.weekly_summary.notes,
    )

    return MealPlanResponse(
        plan_id        = plan_id,
        week_start     = week_start.isoformat(),
        status         = "active",
        days           = days_out,
        weekly_summary = summary,
        calorie_target = state.calorie_target or 0,
        macro_split    = {"protein": mac.protein, "carbs": mac.carbs, "fat": mac.fat} if mac else {},
        grocery_list   = _build_grocery_out(state.grocery_list),
        prep_schedule  = _build_prep_out(state.prep_schedule),
    )


# ═══════════════════════════════════════════════════════════════
# PUBLIC SERVICE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def generate_meal_plan(
    user: User,
    db: Session,
    request: GenerateMealPlanRequest,
) -> MealPlanResponse:
    import asyncio

    state      = _build_weekly_state(user, db, request)
    week_start = _parse_week_start(request.week_start)

    loop  = asyncio.get_event_loop()
    state = await loop.run_in_executor(_executor, _run_weekly_pipeline, state)

    plan_id = _persist_plan(
        user_id    = user.id,
        state      = state,
        week_start = week_start,
        db         = db,
    )

    return _build_plan_response(plan_id, week_start, state)


def get_active_plan(user_id: str, db: Session) -> Optional[MealPlanResponse]:
    """Fetch the user's current active meal plan from DB."""
    from db.models import MealPlan as MealPlanModel, MealPlanItem, Recipe as RecipeModel, RecipeNutrition

    plan_repo = MealPlanRepository(db)
    plan      = plan_repo.get_active_plan(user_id)
    if not plan:
        return None

    # Reconstruct a lightweight response from DB rows
    items = db.query(MealPlanItem).filter_by(plan_id=plan.id).all()

    # Group by day
    from collections import defaultdict
    by_day: dict[str, list[MealPlanItem]] = defaultdict(list)
    for item in items:
        by_day[item.day_of_week].append(item)

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days_out  = []

    for day in day_order:
        if day not in by_day:
            continue
        meals_out = []
        total_cal = total_prot = total_carb = total_fat = total_fib = 0.0

        for item in by_day[day]:
            recipe = db.query(RecipeModel).filter_by(id=item.recipe_id).first()
            nutr   = db.query(RecipeNutrition).filter_by(recipe_id=item.recipe_id).first()
            if recipe and nutr:
                meals_out.append(MealSlotOut(
                    slot=item.meal_slot,
                    dish_name=recipe.name,
                    cuisine=recipe.cuisine,
                    calories=nutr.calories,
                    protein_g=nutr.protein_g,
                    carbs_g=nutr.carbs_g,
                    fat_g=nutr.fat_g,
                    fiber_g=nutr.fiber_g,
                    prep_time_minutes=recipe.prep_time_minutes,
                ))
                total_cal  += nutr.calories
                total_prot += nutr.protein_g
                total_carb += nutr.carbs_g
                total_fat  += nutr.fat_g
                total_fib  += nutr.fiber_g or 0

        days_out.append(DayPlanOut(
            day=day, meals=meals_out,
            total_calories=int(total_cal),
            total_protein_g=total_prot,
            total_carbs_g=total_carb,
            total_fat_g=total_fat,
            total_fiber_g=total_fib,
        ))

    # Build minimal weekly summary from DB data
    avg_cal = sum(d.total_calories for d in days_out) / max(len(days_out), 1)
    summary = WeeklySummaryOut(
        avg_daily_calories=round(avg_cal, 1),
        avg_daily_protein_g=0, avg_daily_carbs_g=0, avg_daily_fat_g=0,
        avg_daily_fiber_g=0, total_weekly_calories=int(avg_cal * len(days_out)),
        calorie_target_hit_days=0, notes="Loaded from database.",
    )

    return MealPlanResponse(
        plan_id        = plan.id,
        week_start     = plan.week_start.isoformat(),
        status         = plan.status,
        days           = days_out,
        weekly_summary = summary,
        calorie_target = 0,
        macro_split    = {},
        grocery_list   = None,
        prep_schedule  = None,
    )


def _build_plan_from_db(plan_id: str, db: Session) -> Optional[MealPlanResponse]:
    """
    Reconstruct a MealPlanResponse for any plan by its ID.
    Used by GET /meal-plans/{plan_id}.
    """
    from db.models import MealPlan as MealPlanModel, MealPlanItem, Recipe as RecipeModel, RecipeNutrition
    from collections import defaultdict

    plan = db.query(MealPlanModel).filter_by(id=plan_id).first()
    if not plan:
        return None

    items = db.query(MealPlanItem).filter_by(plan_id=plan.id).all()

    by_day: dict[str, list[MealPlanItem]] = defaultdict(list)
    for item in items:
        by_day[item.day_of_week].append(item)

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days_out  = []

    for day in day_order:
        if day not in by_day:
            continue
        meals_out = []
        total_cal = total_prot = total_carb = total_fat = total_fib = 0.0

        for item in by_day[day]:
            recipe = db.query(RecipeModel).filter_by(id=item.recipe_id).first()
            nutr   = db.query(RecipeNutrition).filter_by(recipe_id=item.recipe_id).first()
            if recipe and nutr:
                meals_out.append(MealSlotOut(
                    slot=item.meal_slot,
                    dish_name=recipe.name,
                    cuisine=recipe.cuisine,
                    calories=nutr.calories,
                    protein_g=nutr.protein_g,
                    carbs_g=nutr.carbs_g,
                    fat_g=nutr.fat_g,
                    fiber_g=nutr.fiber_g,
                    prep_time_minutes=recipe.prep_time_minutes,
                ))
                total_cal  += nutr.calories
                total_prot += nutr.protein_g
                total_carb += nutr.carbs_g
                total_fat  += nutr.fat_g
                total_fib  += nutr.fiber_g or 0

        days_out.append(DayPlanOut(
            day=day, meals=meals_out,
            total_calories=int(total_cal),
            total_protein_g=total_prot,
            total_carbs_g=total_carb,
            total_fat_g=total_fat,
            total_fiber_g=total_fib,
        ))

    avg_cal = sum(d.total_calories for d in days_out) / max(len(days_out), 1)
    summary = WeeklySummaryOut(
        avg_daily_calories=round(avg_cal, 1),
        avg_daily_protein_g=0, avg_daily_carbs_g=0, avg_daily_fat_g=0,
        avg_daily_fiber_g=0, total_weekly_calories=int(avg_cal * len(days_out)),
        calorie_target_hit_days=0, notes="Loaded from database.",
    )

    return MealPlanResponse(
        plan_id=plan.id,
        week_start=plan.week_start.isoformat(),
        status=plan.status,
        days=days_out,
        weekly_summary=summary,
        calorie_target=0,
        macro_split={},
        grocery_list=None,
        prep_schedule=None,
    )


def list_user_plans(user_id: str, db: Session) -> list[MealPlanSummary]:
    """Return a summary list of all plans for a user."""
    from db.models import MealPlan as MealPlanModel
    rows = (
        db.query(MealPlanModel)
          .filter_by(user_id=user_id)
          .order_by(MealPlanModel.created_at.desc())
          .limit(20)
          .all()
    )
    return [
        MealPlanSummary(
            plan_id=r.id,
            week_start=r.week_start.isoformat(),
            status=r.status,
            avg_daily_calories=0.0,
            calorie_target_hit_days=0,
        )
        for r in rows
    ]