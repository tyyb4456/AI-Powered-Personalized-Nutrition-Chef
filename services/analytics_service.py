"""
api/services/analytics_service.py

Business logic for Phase 5:

1. Progress report  — loads meal logs → calls progress_agent_node (LLM) in thread
2. Learned prefs    — load / manual-update via LearnedPreferencesRepository
3. Learning trigger — runs learning_loop_agent_node on a single feedback entry (LLM)

Both LLM calls run in ThreadPoolExecutor so the async event loop stays free.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from sqlalchemy.orm import Session

from db.models import User, UserFeedback
from db.repositories import (
    UserRepository,
    ProgressRepository,
    LearnedPreferencesRepository,
)
from schemas.nutrition_schemas import (
    LearnedPreferences,
    WeeklyProgressReport,
)
from state import NutritionState
from agents.health_agent import health_goal_agent_node
from agents.progress_agent import progress_agent_node
from agents.learning_loop_agent import learning_loop_agent_node
from schemas.analytics_schemas import (
    GenerateProgressReportRequest,
    ProgressReportResponse,
    LearnedPreferencesResponse,
    UpdateLearnedPreferencesRequest,
    TriggerLearningRequest,
    TriggerLearningResponse,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _prefs_to_response(prefs: LearnedPreferences) -> LearnedPreferencesResponse:
    return LearnedPreferencesResponse(
        liked_ingredients    = prefs.liked_ingredients,
        disliked_ingredients = prefs.disliked_ingredients,
        preferred_textures   = prefs.preferred_textures,
        preferred_cuisines   = prefs.preferred_cuisines,
        avoided_cuisines     = prefs.avoided_cuisines,
        spice_preference     = prefs.spice_preference,
        goal_refinement      = prefs.goal_refinement,
        session_insights     = prefs.session_insights,
    )


def _empty_prefs() -> LearnedPreferencesResponse:
    return LearnedPreferencesResponse(
        liked_ingredients=[], disliked_ingredients=[],
        preferred_textures=[], preferred_cuisines=[],
        avoided_cuisines=[], spice_preference=None,
        goal_refinement=None, session_insights=[],
    )


def _build_nutrition_state(user: User, db: Session) -> NutritionState:
    """Build a NutritionState seeded from the user's saved DB profile."""
    from db.models import UserProfile

    repo    = UserRepository(db)
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    prefs   = repo.get_preferences(user.id)
    allergies  = repo.get_allergies(user.id)
    conditions = repo.get_medical_conditions(user.id)

    return NutritionState(
        customer_id    = user.id,
        name           = user.name,
        age            = profile.age            if profile else None,
        gender         = profile.gender         if profile else None,
        weight_kg      = profile.weight_kg      if profile else None,
        height_cm      = profile.height_cm      if profile else None,
        activity_level = profile.activity_level if profile else "moderate",
        fitness_goal   = prefs.get("fitness_goal", "maintenance"),
        allergies      = allergies,
        medical_conditions = conditions,
        preferences    = {k: v for k, v in prefs.items() if not k.startswith("__")},
        profile_collected = True,
    )


# ═══════════════════════════════════════════════════════════════
# PROGRESS REPORT
# ═══════════════════════════════════════════════════════════════

def _run_progress_pipeline(
    state: NutritionState,
    calorie_target: int,
    days: int,
) -> tuple[WeeklyProgressReport, int]:
    """
    Blocking: calculates health goal then runs progress_agent_node.
    Returns (report, log_count).
    """
    # Ensure calorie_target is set — run health_goal_agent if needed
    if not state.calorie_target:
        updates = health_goal_agent_node(state)
        state   = state.model_copy(update=updates)

    # Allow caller to override
    state = state.model_copy(update={"calorie_target": calorie_target})

    # Load logs early so we can return count without double-querying
    from memory.progress_store import get_logs, get_daily_adherence
    logs      = get_logs(state.customer_id, days=days)
    adherence = get_daily_adherence(state.customer_id, calorie_target, days=days)

    if not logs:
        raise ValueError(
            f"No meal logs found for the last {days} days. "
            "Log some meals first via POST /meal-logs/."
        )

    # Inject pre-loaded data into state for the agent
    # (progress_agent_node re-queries internally, but we need the count here)
    updates = progress_agent_node(state)
    state   = state.model_copy(update=updates)

    if state.pipeline_error:
        raise ValueError(state.pipeline_error)

    return state.progress_report, len(logs)


async def generate_progress_report(
    user: User,
    db: Session,
    request: GenerateProgressReportRequest,
) -> ProgressReportResponse:
    import asyncio

    state = _build_nutrition_state(user, db)

    # Resolve calorie target: request override → DB goal → health agent default
    calorie_target = request.calorie_target
    if not calorie_target:
        goal = UserRepository(db).get_current_goal(user.id)
        calorie_target = goal.calorie_target if goal else 2000

    loop   = asyncio.get_event_loop()
    report, log_count = await loop.run_in_executor(
        _executor,
        _run_progress_pipeline,
        state,
        calorie_target,
        request.days,
    )

    return ProgressReportResponse(
        week_start          = report.week_start,
        week_end            = report.week_end,
        avg_adherence_pct   = report.avg_adherence_pct,
        best_day            = report.best_day,
        worst_day           = report.worst_day,
        patterns_identified = report.patterns_identified,
        recommendations     = report.recommendations,
        goal_progress       = report.goal_progress,
        motivational_note   = report.motivational_note,
        logs_analysed       = log_count,
        calorie_target_used = calorie_target,
    )


# ═══════════════════════════════════════════════════════════════
# LEARNED PREFERENCES
# ═══════════════════════════════════════════════════════════════

def get_learned_preferences(
    user_id: str,
    db: Session,
) -> LearnedPreferencesResponse:
    repo  = LearnedPreferencesRepository(db)
    prefs = repo.load(user_id)
    return _prefs_to_response(prefs) if prefs else _empty_prefs()


def update_learned_preferences(
    user_id: str,
    db: Session,
    payload: UpdateLearnedPreferencesRequest,
) -> LearnedPreferencesResponse:
    """
    Partial-update learned preferences.
    Loads existing, merges in provided fields, saves back.
    """
    repo     = LearnedPreferencesRepository(db)
    existing = repo.load(user_id) or LearnedPreferences(
        liked_ingredients=[], disliked_ingredients=[],
        preferred_textures=[], preferred_cuisines=[],
        avoided_cuisines=[],
    )

    # Merge only provided fields
    merged = existing.model_copy(update={
        k: v for k, v in payload.model_dump(exclude_none=True).items()
    })

    repo.save(user_id, merged)
    db.flush()

    logger.info("Learned preferences manually updated for user %s", user_id)
    return _prefs_to_response(merged)


def reset_learned_preferences(
    user_id: str,
    db: Session,
) -> None:
    """Wipe all learned preference rows for the user."""
    from db.models import LearnedPreference as LPModel
    db.query(LPModel).filter_by(user_id=user_id).delete()
    db.flush()
    logger.info("Learned preferences reset for user %s", user_id)


# ═══════════════════════════════════════════════════════════════
# TRIGGER LEARNING LOOP
# ═══════════════════════════════════════════════════════════════

def _run_learning_pipeline(state: NutritionState) -> NutritionState:
    """Blocking: runs learning_loop_agent_node and returns updated state."""
    updates = learning_loop_agent_node(state)
    return state.model_copy(update=updates)


async def trigger_learning(
    user: User,
    db: Session,
    request: TriggerLearningRequest,
) -> TriggerLearningResponse:
    """
    Manually triggers the learning loop for a specific feedback entry.
    Useful for clients that want to update learned preferences after collecting
    new feedback without waiting for the next recipe generation cycle.
    """
    import asyncio

    # Load the feedback entry
    fb = db.query(UserFeedback).filter_by(
        id=request.feedback_id, user_id=user.id,
    ).first()
    if not fb:
        raise ValueError(f"Feedback '{request.feedback_id}' not found.")

    # Build state with feedback pre-loaded
    state = _build_nutrition_state(user, db)

    # Load existing learned preferences
    lp_repo = LearnedPreferencesRepository(db)
    state   = state.model_copy(update={
        "feedback_rating":    fb.rating,
        "feedback_comment":   fb.comment,
        "feedback_collected": True,
        "learned_preferences": lp_repo.load(user.id),
    })

    # Run in thread (LLM call)
    loop  = asyncio.get_event_loop()
    state = await loop.run_in_executor(_executor, _run_learning_pipeline, state)

    goal_updated = bool(
        state.learned_preferences and state.learned_preferences.goal_refinement
    )

    return TriggerLearningResponse(
        message             = "Learning loop completed. Preferences updated.",
        preferences_updated = True,
        goal_updated        = goal_updated,
        updated_preferences = _prefs_to_response(
            state.learned_preferences or LearnedPreferences(
                liked_ingredients=[], disliked_ingredients=[],
                preferred_textures=[], preferred_cuisines=[], avoided_cuisines=[],
            )
        ),
    )