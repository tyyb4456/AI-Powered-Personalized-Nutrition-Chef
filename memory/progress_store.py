"""
memory/progress_store.py

File-based persistence for meal logs and adherence data.
Phase 4 will replace this with PostgreSQL.

Storage structure (data/progress/{user_id}.json):
{
  "logs": [ MealLogEntry.dict(), ... ],
  "learned_preferences": LearnedPreferences.dict()
}

All public functions work with Pydantic models — callers never
touch raw JSON directly.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from schemas.nutrition_schemas import (
    MealLogEntry,
    DailyAdherence,
    LearnedPreferences,
)

DATA_DIR = Path("data/progress")


def _user_file(user_id: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{user_id}.json"


def _load_raw(user_id: str) -> dict:
    f = _user_file(user_id)
    if not f.exists():
        return {"logs": [], "learned_preferences": None}
    with open(f) as fh:
        return json.load(fh)


def _save_raw(user_id: str, data: dict) -> None:
    with open(_user_file(user_id), "w") as fh:
        json.dump(data, fh, indent=2, default=str)


# ── Public API ────────────────────────────────────────────────────────────────

def log_meal(user_id: str, entry: MealLogEntry) -> None:
    """Append one meal log entry for the user."""
    data = _load_raw(user_id)
    data["logs"].append(entry.model_dump())
    _save_raw(user_id, data)
    print(f"   📝 Logged: {entry.dish_name} ({entry.calories} kcal) on {entry.log_date}")


def get_logs(user_id: str, days: int = 7) -> list[MealLogEntry]:
    """Return logs from the last N days."""
    data  = _load_raw(user_id)
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
    """
    Compute per-day adherence for the last N days.
    planned_calories_per_day comes from state.calorie_target.
    """
    logs    = get_logs(user_id, days=days)
    by_day: dict[str, list[MealLogEntry]] = {}
    for entry in logs:
        by_day.setdefault(entry.log_date, []).append(entry)

    result = []
    for log_date, day_logs in sorted(by_day.items()):
        actual_cal = sum(e.calories for e in day_logs)
        adherence  = (actual_cal / planned_calories_per_day * 100) if planned_calories_per_day else 0
        result.append(DailyAdherence(
            log_date=log_date,
            planned_calories=planned_calories_per_day,
            actual_calories=actual_cal,
            adherence_pct=round(adherence, 1),
            meals_logged=len(day_logs),
            meals_skipped=max(0, 3 - len(day_logs)),   # assumes 3 meals/day
        ))
    return result


def save_learned_preferences(user_id: str, prefs: LearnedPreferences) -> None:
    data = _load_raw(user_id)
    data["learned_preferences"] = prefs.model_dump()
    _save_raw(user_id, data)


def load_learned_preferences(user_id: str) -> Optional[LearnedPreferences]:
    data = _load_raw(user_id)
    raw  = data.get("learned_preferences")
    return LearnedPreferences(**raw) if raw else None


# Fix missing Optional import
from typing import Optional