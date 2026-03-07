"""
db/repositories.py

Repository pattern — one class per domain.
Agents call these instead of writing raw SQLAlchemy queries.

Rule: repositories accept/return Pydantic schemas or plain values.
      They never expose SQLAlchemy ORM objects outside this file.
      This keeps agents completely decoupled from the DB layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models import (
    User, UserProfile, UserGoal, UserMedicalCondition,
    UserAllergy, UserPreference, Recipe, RecipeIngredient,
    RecipeNutrition, MealPlan, MealPlanItem, UserFeedback,
    MealLog, LearnedPreference,
)
from schemas.nutrition_schemas import (
    RecipeOutput, MacroSplit, MedicalCondition,
    LearnedPreferences, MealLogEntry, DailyAdherence,
)


def _uuid() -> str:
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
# USER REPOSITORY
# ═══════════════════════════════════════════════════════════════

class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Optional[User]:
        return self.db.query(User).filter(User.name == name).first()

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create(self, name: str, email: Optional[str] = None) -> User:
        user = User(id=_uuid(), name=name, email=email,
                    created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        self.db.add(user)
        self.db.flush()   # get ID without committing
        return user

    def get_or_create(self, name: str) -> tuple[User, bool]:
        """Returns (user, created: bool)."""
        existing = self.get_by_name(name)
        if existing:
            return existing, False
        user = self.create(name)
        return user, True

    def upsert_profile(
        self, user_id: str, age: int, gender: str,
        weight_kg: float, height_cm: float, activity_level: str,
    ) -> UserProfile:
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        now = datetime.utcnow()
        if profile:
            profile.age            = age
            profile.gender         = gender
            profile.weight_kg      = weight_kg
            profile.height_cm      = height_cm
            profile.activity_level = activity_level
            profile.updated_at     = now
        else:
            profile = UserProfile(
                id=_uuid(), user_id=user_id, age=age, gender=gender,
                weight_kg=weight_kg, height_cm=height_cm,
                activity_level=activity_level, updated_at=now,
            )
            self.db.add(profile)
        self.db.flush()
        return profile

    def save_goal(self, user_id: str, macro: MacroSplit,
                  calorie_target: int, goal_type: str) -> UserGoal:
        goal = UserGoal(
            id=_uuid(), user_id=user_id, goal_type=goal_type,
            calorie_target=calorie_target,
            protein_pct=macro.protein,
            carbs_pct=macro.carbs,
            fat_pct=macro.fat,
            set_at=datetime.utcnow(),
        )
        self.db.add(goal)
        self.db.flush()
        return goal

    def get_current_goal(self, user_id: str) -> Optional[UserGoal]:
        return (
            self.db.query(UserGoal)
            .filter_by(user_id=user_id)
            .order_by(UserGoal.set_at.desc())
            .first()
        )

    def sync_medical_conditions(
        self, user_id: str, conditions: list[MedicalCondition],
    ) -> None:
        """Replace all medical conditions for a user with the new list."""
        self.db.query(UserMedicalCondition).filter_by(user_id=user_id).delete()
        for c in conditions:
            self.db.add(UserMedicalCondition(
                id=_uuid(), user_id=user_id, condition=c.condition,
                notes=c.notes, added_at=datetime.utcnow(),
            ))
        self.db.flush()

    def get_medical_conditions(self, user_id: str) -> list[MedicalCondition]:
        rows = self.db.query(UserMedicalCondition).filter_by(user_id=user_id).all()
        return [MedicalCondition(condition=r.condition, notes=r.notes) for r in rows]  # type: ignore

    def sync_allergies(self, user_id: str, allergens: list[str]) -> None:
        self.db.query(UserAllergy).filter_by(user_id=user_id).delete()
        for allergen in allergens:
            self.db.add(UserAllergy(id=_uuid(), user_id=user_id, allergen=allergen))
        self.db.flush()

    def get_allergies(self, user_id: str) -> list[str]:
        rows = self.db.query(UserAllergy).filter_by(user_id=user_id).all()
        return [r.allergen for r in rows]

    def upsert_preference(self, user_id: str, key: str, value: str) -> None:
        pref = self.db.query(UserPreference).filter_by(user_id=user_id, key=key).first()
        if pref:
            pref.value      = value
            pref.updated_at = datetime.utcnow()
        else:
            self.db.add(UserPreference(
                id=_uuid(), user_id=user_id, key=key,
                value=value, updated_at=datetime.utcnow(),
            ))
        self.db.flush()

    def get_preferences(self, user_id: str) -> dict[str, str]:
        rows = self.db.query(UserPreference).filter_by(user_id=user_id).all()
        return {r.key: r.value for r in rows}

    def save_feedback(
        self, user_id: str, recipe_id: str, rating: int, comment: Optional[str],
    ) -> UserFeedback:
        fb = UserFeedback(
            id=_uuid(), user_id=user_id, recipe_id=recipe_id,
            rating=rating, comment=comment, created_at=datetime.utcnow(),
        )
        self.db.add(fb)
        self.db.flush()
        return fb


# ═══════════════════════════════════════════════════════════════
# RECIPE REPOSITORY
# ═══════════════════════════════════════════════════════════════

class RecipeRepository:

    def __init__(self, db: Session):
        self.db = db

    def save(self, recipe: RecipeOutput, source: str = "generated") -> str:
        """
        Persist a RecipeOutput to the database.
        Returns the new recipe ID.
        """
        recipe_id = _uuid()
        now = datetime.utcnow()

        db_recipe = Recipe(
            id=recipe_id,
            name=recipe.dish_name,
            cuisine=recipe.cuisine,
            meal_type=recipe.meal_type,
            source=source,
            generated_at=now,
            prep_time_minutes=recipe.prep_time_minutes,
        )
        self.db.add(db_recipe)

        # Ingredients
        for ing in recipe.ingredients:
            self.db.add(RecipeIngredient(
                id=_uuid(), recipe_id=recipe_id,
                name=ing.name, quantity=ing.quantity,
            ))

        # Nutrition
        n = recipe.nutrition
        self.db.add(RecipeNutrition(
            id=_uuid(), recipe_id=recipe_id,
            calories=n.calories, protein_g=n.protein_g,
            carbs_g=n.carbs_g, fat_g=n.fat_g,
            fiber_g=n.fiber_g, sodium_mg=n.sodium_mg,
            calcium_mg=n.calcium_mg, iron_mg=n.iron_mg, sugar_g=n.sugar_g,
        ))

        self.db.flush()
        return recipe_id

    def get_by_id(self, recipe_id: str) -> Optional[Recipe]:
        return self.db.query(Recipe).filter_by(id=recipe_id).first()


# ═══════════════════════════════════════════════════════════════
# MEAL PLAN REPOSITORY
# ═══════════════════════════════════════════════════════════════

class MealPlanRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_plan(self, user_id: str, week_start: date) -> str:
        """Creates a new meal plan header and returns its ID."""
        # Archive any existing active plan for this week
        (
            self.db.query(MealPlan)
            .filter_by(user_id=user_id, week_start=week_start, status="active")
            .update({"status": "archived"})
        )
        plan = MealPlan(
            id=_uuid(), user_id=user_id,
            week_start=week_start, status="active",
            created_at=datetime.utcnow(),
        )
        self.db.add(plan)
        self.db.flush()
        return plan.id

    def add_item(
        self, plan_id: str, recipe_id: str,
        day_of_week: str, meal_slot: str,
    ) -> None:
        self.db.add(MealPlanItem(
            id=_uuid(), plan_id=plan_id, recipe_id=recipe_id,
            day_of_week=day_of_week, meal_slot=meal_slot,
        ))

    def get_active_plan(self, user_id: str) -> Optional[MealPlan]:
        return (
            self.db.query(MealPlan)
            .filter_by(user_id=user_id, status="active")
            .order_by(MealPlan.created_at.desc())
            .first()
        )


# ═══════════════════════════════════════════════════════════════
# PROGRESS REPOSITORY
# ═══════════════════════════════════════════════════════════════

class ProgressRepository:

    def __init__(self, db: Session):
        self.db = db

    def log_meal(self, user_id: str, entry: MealLogEntry, recipe_id: Optional[str] = None) -> str:
        log_id = _uuid()
        self.db.add(MealLog(
            id=log_id, user_id=user_id, recipe_id=recipe_id,
            log_date=date.fromisoformat(entry.log_date),
            meal_slot=entry.meal_slot, dish_name=entry.dish_name,
            planned=entry.planned, portion_multiplier=1.0,
            calories=entry.calories, protein_g=entry.protein_g,
            carbs_g=entry.carbs_g, fat_g=entry.fat_g,
            source=entry.source, logged_at=datetime.utcnow(),
        ))
        self.db.flush()
        return log_id

    def get_logs(self, user_id: str, days: int = 7) -> list[MealLogEntry]:
        cutoff = date.today() - timedelta(days=days)
        rows = (
            self.db.query(MealLog)
            .filter(MealLog.user_id == user_id, MealLog.log_date >= cutoff)
            .order_by(MealLog.log_date.asc(), MealLog.logged_at.asc())
            .all()
        )
        return [
            MealLogEntry(
                log_date=str(r.log_date),
                meal_slot=r.meal_slot,
                dish_name=r.dish_name,
                planned=r.planned,
                calories=r.calories,
                protein_g=r.protein_g,
                carbs_g=r.carbs_g,
                fat_g=r.fat_g,
                source=r.source,
            )
            for r in rows
        ]

    def get_daily_adherence(
        self, user_id: str, planned_calories_per_day: int, days: int = 7,
    ) -> list[DailyAdherence]:
        logs    = self.get_logs(user_id, days)
        by_day: dict[str, list[MealLogEntry]] = {}
        for entry in logs:
            by_day.setdefault(entry.log_date, []).append(entry)

        result = []
        for log_date, day_logs in sorted(by_day.items()):
            actual = sum(e.calories for e in day_logs)
            pct    = (actual / planned_calories_per_day * 100) if planned_calories_per_day else 0
            result.append(DailyAdherence(
                log_date=log_date,
                planned_calories=planned_calories_per_day,
                actual_calories=actual,
                adherence_pct=round(pct, 1),
                meals_logged=len(day_logs),
                meals_skipped=max(0, 3 - len(day_logs)),
            ))
        return result


# ═══════════════════════════════════════════════════════════════
# LEARNED PREFERENCES REPOSITORY
# ═══════════════════════════════════════════════════════════════

class LearnedPreferencesRepository:

    def __init__(self, db: Session):
        self.db = db

    def save(self, user_id: str, prefs: LearnedPreferences) -> None:
        """
        Persist all fields of a LearnedPreferences object.
        Each field becomes a row with key=field_name, value=comma-separated list.
        """
        field_map = {
            "liked_ingredients":    ", ".join(prefs.liked_ingredients),
            "disliked_ingredients": ", ".join(prefs.disliked_ingredients),
            "preferred_textures":   ", ".join(prefs.preferred_textures),
            "preferred_cuisines":   ", ".join(prefs.preferred_cuisines),
            "avoided_cuisines":     ", ".join(prefs.avoided_cuisines),
            "spice_preference":     prefs.spice_preference or "",
            "goal_refinement":      prefs.goal_refinement  or "",
            "session_insights":     " | ".join(prefs.session_insights),
        }

        for key, value in field_map.items():
            existing = (
                self.db.query(LearnedPreference)
                .filter_by(user_id=user_id, key=key)
                .first()
            )
            now = datetime.utcnow()
            if existing:
                existing.value      = value
                existing.updated_at = now
            else:
                self.db.add(LearnedPreference(
                    id=_uuid(), user_id=user_id, key=key,
                    value=value, confidence=1.0, updated_at=now,
                ))
        self.db.flush()

    def load(self, user_id: str) -> Optional[LearnedPreferences]:
        rows = self.db.query(LearnedPreference).filter_by(user_id=user_id).all()
        if not rows:
            return None

        data = {r.key: r.value for r in rows}

        def split(val: str) -> list[str]:
            return [x.strip() for x in val.split(",") if x.strip()] if val else []

        return LearnedPreferences(
            liked_ingredients    = split(data.get("liked_ingredients", "")),
            disliked_ingredients = split(data.get("disliked_ingredients", "")),
            preferred_textures   = split(data.get("preferred_textures", "")),
            preferred_cuisines   = split(data.get("preferred_cuisines", "")),
            avoided_cuisines     = split(data.get("avoided_cuisines", "")),
            spice_preference     = data.get("spice_preference") or None,
            goal_refinement      = data.get("goal_refinement")  or None,
            session_insights     = [x.strip() for x in data.get("session_insights", "").split("|") if x.strip()],
        )