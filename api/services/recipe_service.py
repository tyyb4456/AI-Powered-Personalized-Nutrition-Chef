"""
api/services/recipe_service.py

Business logic for recipe generation.

Key design:
  - Loads the user's full profile from DB to seed NutritionState
  - Runs ONLY the agents needed: health_goal → recipe → validate → substitute → explain
    (profile_agent and feedback_agent are SKIPPED — profile comes from DB, 
     feedback is collected via a separate POST /feedback endpoint)
  - Runs the LangGraph pipeline synchronously inside a ThreadPoolExecutor
    so FastAPI's async event loop is not blocked
  - Returns a fully-populated RecipeResponse

Pipeline nodes run (in order):
  health_goal_agent_node   → calorie target + macro split
  recipe_generator_node    → LLM recipe generation (with RAG + Redis cache)
  nutrition_validation_agent_node → validates macros / allergens / fiber
  macro_adjustment_agent_node     → auto-fixes if validation fails (up to 2 retries)
  substitution_agent_node         → allergen substitutions
  explainability_agent_node       → why this recipe?
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from sqlalchemy.orm import Session

from state import NutritionState
from schemas.nutrition_schemas import MedicalCondition, MacroSplit
from db.models import User
from db.repositories import UserRepository, RecipeRepository
from agents.health_agent            import health_goal_agent_node
from agents.recipe_agent            import recipe_generator_node
from agents.nutrition_validator     import nutrition_validation_agent_node
from agents.macro_adjustment_agent  import macro_adjustment_agent_node
from agents.substitution_agent      import substitution_agent_node
from agents.explainability_agent    import explainability_agent_node
from agents.followup_agent          import followup_agent_node
from schemas.recipe_schemas     import (
    GenerateRecipeRequest, RecipeResponse, RecipeSummary, RecipeListResponse,
    IngredientOut, NutritionOut, SubstitutionOut, ValidationOut, FollowupResponse
)

logger = logging.getLogger(__name__)

# Shared thread pool — reused across requests (avoid spawning threads per-call)
_executor = ThreadPoolExecutor(max_workers=4)

MAX_RETRIES = 2


# ═══════════════════════════════════════════════════════════════
# STATE BUILDER
# ═══════════════════════════════════════════════════════════════

def _build_state_from_profile(
    user: User,
    db: Session,
    request: GenerateRecipeRequest,
) -> NutritionState:
    """
    Load the user's saved profile from DB and construct a NutritionState.
    Request fields override profile values when provided.
    """
    repo    = UserRepository(db)
    profile = db.query(__import__("db.models", fromlist=["UserProfile"]).UserProfile)\
                .filter_by(user_id=user.id).first()
    prefs      = repo.get_preferences(user.id)
    allergies  = repo.get_allergies(user.id)
    conditions = repo.get_medical_conditions(user.id)

    # Merge request allergies with profile allergies (deduplicated)
    all_allergies = list(set(allergies + request.extra_allergies))

    # Request fields override profile preferences
    cuisine     = request.cuisine     or prefs.get("cuisine", "any")
    spice_level = request.spice_level or prefs.get("spice_level", "medium")
    fitness_goal = request.fitness_goal or prefs.get("fitness_goal", "maintenance")

    return NutritionState(
        # Identity
        customer_id = user.id,
        name        = user.name,
        session_id  = None,

        # Physical stats from profile
        age            = profile.age            if profile else None,
        gender         = profile.gender         if profile else None,
        weight_kg      = profile.weight_kg      if profile else None,
        height_cm      = profile.height_cm      if profile else None,
        activity_level = profile.activity_level if profile else "moderate",

        # Health & preferences
        fitness_goal        = fitness_goal,
        allergies           = all_allergies,
        medical_conditions  = conditions,
        preferences         = {
            "cuisine":     cuisine,
            "spice_level": spice_level,
            **({"meal_type": request.meal_type} if request.meal_type else {}),
        },

        profile_collected = True,   # skip profile_agent
    )


# ═══════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════

def _run_pipeline(state: NutritionState) -> NutritionState:
    """
    Executes the agent pipeline synchronously (called from ThreadPoolExecutor).

    Runs agents directly (no LangGraph graph) to avoid the interrupt()
    mechanism used by the CLI pipeline. Feedback is collected separately.
    """

    # ── Step 1: Health goal → calorie target + macro split ───────────────────
    updates = health_goal_agent_node(state)
    state   = state.model_copy(update=updates)

    # ── Step 2: Generate recipe (LLM call, Redis-cached) ─────────────────────
    updates = recipe_generator_node(state)
    state   = state.model_copy(update=updates)

    if not state.generated_recipe:
        raise ValueError("Recipe generation failed — no recipe returned by LLM.")

    # ── Step 3: Validate + auto-retry with macro adjustment ───────────────────
    retry = 0
    while retry <= MAX_RETRIES:
        updates = nutrition_validation_agent_node(state)
        state   = state.model_copy(update=updates)

        if state.validation_passed:
            break

        if retry < MAX_RETRIES:
            logger.info("Validation failed (retry %d/%d) — running macro adjustment.", retry + 1, MAX_RETRIES)
            updates = macro_adjustment_agent_node(state)
            state   = state.model_copy(update=updates)
            retry  += 1
        else:
            logger.warning("Max retries reached — accepting best-effort recipe.")
            break

    # ── Step 4: Allergen substitutions ────────────────────────────────────────
    updates = substitution_agent_node(state)
    state   = state.model_copy(update=updates)

    # ── Step 5: Explanation ───────────────────────────────────────────────────
    updates = explainability_agent_node(state)
    state   = state.model_copy(update=updates)

    return state

# ═══════════════════════════════════════════════════════════════
# RECIPE SUB-PIPELINE (validate → substitute → explain)
# Extracted so it can be reused on regeneration
# ═══════════════════════════════════════════════════════════════

def _run_post_generation_steps(state: NutritionState) -> NutritionState:
    """
    Runs validation → macro-adjustment → substitution → explanation.
    Called both by the initial pipeline and by the regeneration branch.
    """
    retry = 0
    while retry <= MAX_RETRIES:
        updates = nutrition_validation_agent_node(state)
        state   = state.model_copy(update=updates)
        if state.validation_passed:
            break
        if retry < MAX_RETRIES:
            logger.info("Validation failed (retry %d/%d) — running macro adjustment.", retry + 1, MAX_RETRIES)
            updates = macro_adjustment_agent_node(state)
            state   = state.model_copy(update=updates)
            retry  += 1
        else:
            logger.warning("Max retries reached — accepting best-effort recipe.")
            break

    updates = substitution_agent_node(state)
    state   = state.model_copy(update=updates)

    updates = explainability_agent_node(state)
    state   = state.model_copy(update=updates)

    return state


def _run_followup_pipeline(state: NutritionState) -> NutritionState:
    """
    Runs followup_agent_node.

    Conditional edge logic (replaces LangGraph router):
      "question" → state has followup_answer populated; return immediately
      "modify"   → re-run recipe_generator_node + post-generation steps
      "done"     → return state unchanged
    """
    # ── Node: classify intent and prepare response / modification ─────────────
    updates = followup_agent_node(state)
    state   = state.model_copy(update=updates)

    intent = state.followup_intent

    # ── Conditional edge ──────────────────────────────────────────────────────

    if intent == "question":
        # Answer already populated by followup_agent_node — nothing more to do
        logger.info("Follow-up intent: question — answer ready.")
        return state

    elif intent == "modify":
        # Inject the modification instruction as extra context for the recipe generator.
        # We store it in preferences so recipe_generator_node picks it up naturally.
        logger.info("Follow-up intent: modify — regenerating recipe.")

        updated_prefs = {
            **state.preferences,
            "followup_modification": state.followup_modification,
        }
        state = state.model_copy(update={"preferences": updated_prefs})

        # Re-run recipe generation (health goal calorie target is already set)
        updates = recipe_generator_node(state)
        state   = state.model_copy(update=updates)

        if not state.generated_recipe:
            raise ValueError("Recipe regeneration failed — no recipe returned by LLM.")

        # Run the full post-generation pipeline again
        state = _run_post_generation_steps(state)
        return state

    else:
        # intent == "done" (or unexpected value)
        logger.info("Follow-up intent: done — no further action.")
        return state


# ═══════════════════════════════════════════════════════════════
# RESPONSE BUILDER
# ═══════════════════════════════════════════════════════════════

def _build_response(state: NutritionState, recipe_id: str) -> RecipeResponse:
    """Map NutritionState → RecipeResponse."""
    recipe     = state.final_recipe
    validation = state.validation_result
    sub_output = state.substitution_output

    nutrition = NutritionOut(
        calories   = recipe.nutrition.calories,
        protein_g  = recipe.nutrition.protein_g,
        carbs_g    = recipe.nutrition.carbs_g,
        fat_g      = recipe.nutrition.fat_g,
        fiber_g    = recipe.nutrition.fiber_g,
        sodium_mg  = recipe.nutrition.sodium_mg,
        calcium_mg = recipe.nutrition.calcium_mg,
        iron_mg    = recipe.nutrition.iron_mg,
        sugar_g    = recipe.nutrition.sugar_g,
    )

    substitutions = []
    if sub_output and sub_output.substitutions_made:
        substitutions = [
            SubstitutionOut(
                original   = s.original_ingredient,
                substitute = s.substitute_ingredient,
                reason     = s.reason,
            )
            for s in sub_output.substitutions
        ]

    validation_out = ValidationOut(
        passed           = validation.passed          if validation else True,
        calorie_check    = validation.calorie_check   if validation else True,
        protein_check    = validation.protein_check   if validation else True,
        carbs_check      = validation.carbs_check     if validation else True,
        fat_check        = validation.fat_check       if validation else True,
        fiber_check      = validation.fiber_check     if validation else True,
        allergen_check   = validation.allergen_check  if validation else True,
        calorie_diff_pct = validation.calorie_diff_pct if validation else 0.0,
        notes            = validation.notes           if validation else "",
    )

    macro = state.macro_split
    return RecipeResponse(
        recipe_id         = recipe_id,
        dish_name         = recipe.dish_name,
        cuisine           = recipe.cuisine,
        meal_type         = recipe.meal_type,
        prep_time_minutes = recipe.prep_time_minutes,
        ingredients       = [IngredientOut(name=i.name, quantity=i.quantity) for i in recipe.ingredients],
        steps             = recipe.steps,
        nutrition         = nutrition,
        substitutions     = substitutions,
        explanation       = state.recipe_explanation,
        validation        = validation_out,
        calorie_target    = state.calorie_target or 0,
        macro_split       = {"protein": macro.protein, "carbs": macro.carbs, "fat": macro.fat} if macro else {},
        from_cache        = False,
    )


# ═══════════════════════════════════════════════════════════════
# PUBLIC SERVICE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def generate_recipe(
    user: User,
    db: Session,
    request: GenerateRecipeRequest,
) -> RecipeResponse:
    """
    Main entry point called by the router.
    Builds state → runs pipeline in thread → saves to DB → returns response.
    """
    import asyncio

    # ── Build initial state ───────────────────────────────────────────────────
    state = _build_state_from_profile(user, db, request)

    # ── Run pipeline off the event loop (LLM calls are blocking) ─────────────
    loop  = asyncio.get_event_loop()
    state = await loop.run_in_executor(_executor, _run_pipeline, state)

    if not state.final_recipe:
        raise ValueError("Pipeline completed but no final recipe in state.")

    # ── Persist to DB ─────────────────────────────────────────────────────────
    recipe_repo = RecipeRepository(db)
    recipe_id   = recipe_repo.save(state.final_recipe, source="generated", explanation=state.recipe_explanation)
    db.flush()

    logger.info("Recipe '%s' saved (id=%s) for user %s",
                state.final_recipe.dish_name, recipe_id, user.id)

    return _build_response(state, recipe_id)

async def followup_recipe(
    user: User,
    db: Session,
    recipe_id: str,
    prompt: str,
) -> "FollowupResponse":
    """
    Entry point for POST /recipes/{recipe_id}/followup

    1. Loads the saved recipe + user profile from DB to rebuild NutritionState
    2. Reconstructs RecipeOutput from the DB relationships (ingredients + nutrition)
    3. Runs _run_followup_pipeline() in a thread
    4. Returns a FollowupResponse (either an answer or the regenerated recipe)
    """
    import asyncio
    from schemas.recipe_schemas import FollowupResponse
    from schemas.nutrition_schemas import (
        RecipeOutput, Ingredient, NutritionFacts,
    )

    loop = asyncio.get_event_loop()

    # ── Load saved Recipe row from DB ─────────────────────────────────────────
    recipe_repo = RecipeRepository(db)
    saved       = recipe_repo.get_by_id(recipe_id)
    if not saved:
        raise ValueError(f"Recipe '{recipe_id}' not found.")

    # ── Reconstruct RecipeOutput from ORM relationships ───────────────────────
    # The Recipe model stores ingredients/nutrition as related rows,
    # not as a single JSON blob — so we rebuild the Pydantic object here.
    n = saved.nutrition   # RecipeNutrition ORM row (may be None if data is missing)

    final_recipe = RecipeOutput(
        dish_name         = saved.name,
        cuisine           = saved.cuisine,
        meal_type         = saved.meal_type,
        prep_time_minutes = saved.prep_time_minutes,
        ingredients       = [
            Ingredient(name=i.name, quantity=i.quantity)
            for i in (saved.ingredients or [])
        ],
        # Steps are not persisted in the DB schema — pass empty list.
        # The follow-up agent will still answer questions using the ingredient
        # + nutrition context, which is sufficient for Q&A.
        # For modify intent, the LLM regenerates fresh steps anyway.
        steps             = [],
        nutrition         = NutritionFacts(
            calories   = n.calories   if n else 0,
            protein_g  = n.protein_g  if n else 0.0,
            carbs_g    = n.carbs_g    if n else 0.0,
            fat_g      = n.fat_g      if n else 0.0,
            fiber_g    = n.fiber_g    if n else None,
            sodium_mg  = n.sodium_mg  if n else None,
            calcium_mg = n.calcium_mg if n else None,
            iron_mg    = n.iron_mg    if n else None,
            sugar_g    = n.sugar_g    if n else None,
        ),
    )

    # ── Re-build NutritionState from user profile + restored recipe ───────────
    base_request = GenerateRecipeRequest()
    state        = _build_state_from_profile(user, db, base_request)

    # Run health_goal_agent to restore calorie_target + macro_split
    # (needed if intent == "modify" and recipe regeneration is triggered)
    from agents.health_agent import health_goal_agent_node
    updates = health_goal_agent_node(state)
    state   = state.model_copy(update=updates)

    state = state.model_copy(update={
        "final_recipe":      final_recipe,
        "recipe_explanation": None,        # not stored in DB — omit gracefully
        "current_recipe_id": recipe_id,
        "followup_prompt":   prompt,
    })

    # ── Run follow-up pipeline in thread ──────────────────────────────────────
    state = await loop.run_in_executor(_executor, _run_followup_pipeline, state)

    # ── Build response ────────────────────────────────────────────────────────
    intent = state.followup_intent

    if intent == "question":
        return FollowupResponse(
            intent          = "question",
            answer          = state.followup_answer,
            recipe          = None,
            followup_history = state.followup_history,
        )

    elif intent == "modify":
        # Save the regenerated recipe
        new_recipe_id = recipe_repo.save(state.final_recipe, source="regenerated")
        return FollowupResponse(
            intent          = "modify",
            answer          = None,
            recipe          = _build_response(state, new_recipe_id),
            followup_history = state.followup_history,
        )

    else:  # "done"
        return FollowupResponse(
            intent          = "done",
            answer          = "You're all set! Enjoy your meal. 🍽️",
            recipe          = None,
            followup_history = state.followup_history,
        )


def get_recipe_by_id(recipe_id: str, db: Session) -> Optional[RecipeResponse]:
    """Fetch a single recipe by its DB id — full detail including ingredients and steps."""
    from db.models import Recipe as RecipeModel, RecipeNutrition, RecipeIngredient, RecipeStep

    row = db.query(RecipeModel).filter_by(id=recipe_id).first()
    if not row:
        return None

    nutrition = db.query(RecipeNutrition).filter_by(recipe_id=recipe_id).first()
    ingredients = db.query(RecipeIngredient).filter_by(recipe_id=recipe_id).all()
    steps = (
        db.query(RecipeStep)
        .filter_by(recipe_id=recipe_id)
        .order_by(RecipeStep.step_number)
        .all()
    )

    nutrition_out = NutritionOut(
        calories   = nutrition.calories   if nutrition else 0,
        protein_g  = nutrition.protein_g  if nutrition else 0.0,
        carbs_g    = nutrition.carbs_g    if nutrition else 0.0,
        fat_g      = nutrition.fat_g      if nutrition else 0.0,
        fiber_g    = nutrition.fiber_g    if nutrition else None,
        sodium_mg  = nutrition.sodium_mg  if nutrition else None,
        calcium_mg = nutrition.calcium_mg if nutrition else None,
        iron_mg    = nutrition.iron_mg    if nutrition else None,
        sugar_g    = nutrition.sugar_g    if nutrition else None,
    ) if nutrition else NutritionOut(calories=0, protein_g=0, carbs_g=0, fat_g=0)

    return RecipeResponse(
        recipe_id         = row.id,
        dish_name         = row.name,
        cuisine           = row.cuisine,
        meal_type         = row.meal_type,
        prep_time_minutes = row.prep_time_minutes,
        ingredients       = [IngredientOut(name=i.name, quantity=i.quantity) for i in ingredients],
        steps             = [s.instruction for s in steps],
        nutrition         = nutrition_out,
        substitutions     = [],
        explanation       = row.explanation,
        validation        = ValidationOut(passed=True, calorie_check=True, protein_check=True,
                               carbs_check=True, fat_check=True, fiber_check=True,
                               allergen_check=True, calorie_diff_pct=0.0, notes=""),
        calorie_target    = 0,
        macro_split       = {},
        from_cache        = False,
    )

def list_user_recipes(
    user_id: str,
    db: Session,
    page: int = 1,
    limit: int = 10,
) -> RecipeListResponse:
    """
    List all recipes ever generated for a user via their meal logs / feedback.
    Falls back to listing all recipes saved in the recipe table ordered by date.
    """
    from db.models import Recipe as RecipeModel, RecipeNutrition, UserFeedback

    offset = (page - 1) * limit

    # Get recipes linked to this user via feedback (most recent first)
    subq = (
        db.query(UserFeedback.recipe_id)
          .filter_by(user_id=user_id)
          .subquery()
    )

    rows = (
        db.query(RecipeModel)
          .filter(RecipeModel.id.in_(subq))
          .order_by(RecipeModel.generated_at.desc())
          .offset(offset)
          .limit(limit)
          .all()
    )

    total = db.query(RecipeModel).filter(RecipeModel.id.in_(subq)).count()

    summaries = []
    for row in rows:
        nutrition = db.query(RecipeNutrition).filter_by(recipe_id=row.id).first()
        summaries.append(RecipeSummary(
            recipe_id = row.id,
            dish_name = row.name,
            cuisine   = row.cuisine,
            meal_type = row.meal_type,
            calories  = nutrition.calories  if nutrition else 0,
            protein_g = nutrition.protein_g if nutrition else 0.0,
            carbs_g   = nutrition.carbs_g   if nutrition else 0.0,
            fat_g     = nutrition.fat_g     if nutrition else 0.0,
        ))

    return RecipeListResponse(
        recipes = summaries,
        total   = total,
        page    = page,
        limit   = limit,
    )