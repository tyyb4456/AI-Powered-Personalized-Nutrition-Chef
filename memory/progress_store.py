"""
memory/progress_store.py — Phase 4

Replaces JSON file storage with PostgreSQL via ProgressRepository.

Public API is identical to Phase 3 so agents don't need to change.
Falls back to the old JSON file if DB is unavailable (graceful degradation).
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from schemas.nutrition_schemas import MealLogEntry, DailyAdherence, LearnedPreferences

logger = logging.getLogger(__name__)

# ── JSON fallback path (Phase 3 behaviour) ────────────────────────────────────
DATA_DIR = Path("data/progress")


def _json_file(user_id: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{user_id}.json"


def _load_json(user_id: str) -> dict:
    f = _json_file(user_id)
    if not f.exists():
        return {"logs": [], "learned_preferences": None}
    with open(f) as fh:
        return json.load(fh)


def _save_json(user_id: str, data: dict) -> None:
    with open(_json_file(user_id), "w") as fh:
        json.dump(data, fh, indent=2, default=str)


# ── Public API ────────────────────────────────────────────────────────────────

def log_meal(user_id: str, entry: MealLogEntry, recipe_id: Optional[str] = None) -> None:
    """
    Log a consumed meal.
    Writes to PostgreSQL first; falls back to JSON if DB unavailable.
    """
    try:
        from db.database import get_db
        from db.repositories import ProgressRepository
        with get_db() as db:
            repo = ProgressRepository(db)
            repo.log_meal(user_id, entry, recipe_id=recipe_id)
        logger.info("Meal logged to DB: %s (%d kcal)", entry.dish_name, entry.calories)
        print(f"   📝 Logged to DB: {entry.dish_name} ({entry.calories} kcal) on {entry.log_date}")
        return
    except Exception as e:
        logger.warning("DB log_meal failed (%s) — falling back to JSON.", e)

    # ── JSON fallback ─────────────────────────────────────────────────────────
    data = _load_json(user_id)
    data["logs"].append(entry.model_dump())
    _save_json(user_id, data)
    print(f"   📝 Logged to file: {entry.dish_name} ({entry.calories} kcal) on {entry.log_date}")


def get_logs(user_id: str, days: int = 7) -> list[MealLogEntry]:
    """Return meal logs for the last N days from PostgreSQL or JSON fallback."""
    try:
        from db.database import get_db
        from db.repositories import ProgressRepository
        with get_db() as db:
            return ProgressRepository(db).get_logs(user_id, days)
    except Exception as e:
        logger.warning("DB get_logs failed (%s) — falling back to JSON.", e)

    # ── JSON fallback ─────────────────────────────────────────────────────────
    data   = _load_json(user_id)
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return [
        MealLogEntry(**e)
        for e in data["logs"]
        if e.get("log_date", "") >= cutoff
    ]


def get_daily_adherence(
    user_id: str,
    planned_calories_per_day: int,
    days: int = 7,
) -> list[DailyAdherence]:
    """Compute per-day adherence. Uses PostgreSQL or JSON fallback."""
    try:
        from db.database import get_db
        from db.repositories import ProgressRepository
        with get_db() as db:
            return ProgressRepository(db).get_daily_adherence(
                user_id, planned_calories_per_day, days
            )
    except Exception as e:
        logger.warning("DB get_daily_adherence failed (%s) — computing from JSON.", e)

    # ── JSON fallback: compute from raw logs ──────────────────────────────────
    from schemas.nutrition_schemas import DailyAdherence as DA
    logs    = get_logs(user_id, days)
    by_day: dict[str, list[MealLogEntry]] = {}
    for entry in logs:
        by_day.setdefault(entry.log_date, []).append(entry)

    result = []
    for log_date, day_logs in sorted(by_day.items()):
        actual = sum(e.calories for e in day_logs)
        pct    = (actual / planned_calories_per_day * 100) if planned_calories_per_day else 0
        result.append(DA(
            log_date=log_date,
            planned_calories=planned_calories_per_day,
            actual_calories=actual,
            adherence_pct=round(pct, 1),
            meals_logged=len(day_logs),
            meals_skipped=max(0, 3 - len(day_logs)),
        ))
    return result


def save_learned_preferences(user_id: str, prefs: LearnedPreferences) -> None:
    """Persist LearnedPreferences to PostgreSQL and ChromaDB."""
    try:
        from db.database import get_db
        from db.repositories import LearnedPreferencesRepository
        with get_db() as db:
            LearnedPreferencesRepository(db).save(user_id, prefs)
        logger.info("Learned preferences saved to DB for user %s", user_id)
    except Exception as e:
        logger.warning("DB save_learned_preferences failed (%s) — saving to JSON.", e)
        data = _load_json(user_id)
        data["learned_preferences"] = prefs.model_dump()
        _save_json(user_id, data)

    # ── Also update ChromaDB preference embedding ─────────────────────────────
    try:
        from vector_store.chroma_store import chroma_store
        pref_text = (
            f"Likes: {', '.join(prefs.liked_ingredients)}. "
            f"Dislikes: {', '.join(prefs.disliked_ingredients)}. "
            f"Cuisines: {', '.join(prefs.preferred_cuisines)}. "
            f"Spice: {prefs.spice_preference or 'medium'}. "
            f"Goal: {prefs.goal_refinement or 'general fitness'}."
        )
        chroma_store.upsert_user_preferences(user_id, pref_text)
    except Exception as e:
        logger.warning("ChromaDB preference upsert failed: %s", e)


def load_learned_preferences(user_id: str) -> Optional[LearnedPreferences]:
    """Load LearnedPreferences from PostgreSQL or JSON fallback."""
    try:
        from db.database import get_db
        from db.repositories import LearnedPreferencesRepository
        with get_db() as db:
            return LearnedPreferencesRepository(db).load(user_id)
    except Exception as e:
        logger.warning("DB load_learned_preferences failed (%s) — loading from JSON.", e)

    data = _load_json(user_id)
    raw  = data.get("learned_preferences")
    return LearnedPreferences(**raw) if raw else None