"""
db/models.py

SQLAlchemy ORM models for the Nutrition AI system.

Tables:
  users                 — core identity
  user_profiles         — physical stats (weight, height, etc.)
  user_goals            — active calorie/macro targets
  medical_conditions    — per-user health flags
  user_allergies        — allergen list
  user_preferences      — key/value store for cuisine, spice, etc.

  recipes               — generated dish metadata
  recipe_ingredients    — per-recipe ingredient rows
  recipe_nutrition      — per-recipe macro/micro data

  meal_plans            — weekly plan header
  meal_plan_items       — one row per meal slot per day

  user_feedback         — ratings + comments per recipe
  meal_logs             — actual meals consumed (vs planned)
  learned_preferences   — structured preference updates from learning loop

Relationships are declared with back_populates so ORM queries stay clean.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, Date,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


# ── Base ──────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
# USER DOMAIN
# ═══════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id:         Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    name:       Mapped[str]      = mapped_column(String(100), nullable=False)
    email:      Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile:             Mapped[UserProfile | None]        = relationship("UserProfile",          back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals:               Mapped[list[UserGoal]]            = relationship("UserGoal",             back_populates="user", cascade="all, delete-orphan")
    medical_conditions:  Mapped[list[UserMedicalCondition]] = relationship("UserMedicalCondition", back_populates="user", cascade="all, delete-orphan")
    allergies:           Mapped[list[UserAllergy]]         = relationship("UserAllergy",          back_populates="user", cascade="all, delete-orphan")
    preferences:         Mapped[list[UserPreference]]      = relationship("UserPreference",       back_populates="user", cascade="all, delete-orphan")
    feedback:            Mapped[list[UserFeedback]]        = relationship("UserFeedback",         back_populates="user", cascade="all, delete-orphan")
    meal_logs:           Mapped[list[MealLog]]             = relationship("MealLog",              back_populates="user", cascade="all, delete-orphan")
    meal_plans:          Mapped[list[MealPlan]]            = relationship("MealPlan",             back_populates="user", cascade="all, delete-orphan")
    learned_preferences: Mapped[list[LearnedPreference]]  = relationship("LearnedPreference",    back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id:             Mapped[str]        = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id:        Mapped[str]        = mapped_column(String(36), ForeignKey("users.id"), unique=True)
    age:            Mapped[int|None]   = mapped_column(Integer,    nullable=True)
    gender:         Mapped[str|None]   = mapped_column(String(10), nullable=True)
    weight_kg:      Mapped[float|None] = mapped_column(Float,      nullable=True)
    height_cm:      Mapped[float|None] = mapped_column(Float,      nullable=True)
    activity_level: Mapped[str|None]   = mapped_column(String(20), nullable=True)
    updated_at:     Mapped[datetime]   = mapped_column(DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="profile")


class UserGoal(Base):
    """
    Stores calorie target + macro split at a point in time.
    A user may have multiple rows — current goal = most recent set_at.
    """
    __tablename__ = "user_goals"

    id:             Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id:        Mapped[str]      = mapped_column(String(36), ForeignKey("users.id"))
    goal_type:      Mapped[str]      = mapped_column(String(30))   # muscle_gain / fat_loss / maintenance
    calorie_target: Mapped[int]      = mapped_column(Integer)
    protein_pct:    Mapped[int]      = mapped_column(Integer)
    carbs_pct:      Mapped[int]      = mapped_column(Integer)
    fat_pct:        Mapped[int]      = mapped_column(Integer)
    set_at:         Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="goals")

    __table_args__ = (
        Index("ix_user_goals_user_set", "user_id", "set_at"),
    )


class UserMedicalCondition(Base):
    __tablename__ = "medical_conditions"

    id:        Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id:   Mapped[str]      = mapped_column(String(36), ForeignKey("users.id"))
    condition: Mapped[str]      = mapped_column(String(50))
    notes:     Mapped[str|None] = mapped_column(Text, nullable=True)
    added_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="medical_conditions")

    __table_args__ = (
        UniqueConstraint("user_id", "condition", name="uq_user_condition"),
    )


class UserAllergy(Base):
    __tablename__ = "user_allergies"

    id:       Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id:  Mapped[str]      = mapped_column(String(36), ForeignKey("users.id"))
    allergen: Mapped[str]      = mapped_column(String(100))
    severity: Mapped[str|None] = mapped_column(String(20), nullable=True)   # mild / moderate / severe

    user: Mapped[User] = relationship("User", back_populates="allergies")

    __table_args__ = (
        UniqueConstraint("user_id", "allergen", name="uq_user_allergen"),
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id:      Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str]      = mapped_column(String(36), ForeignKey("users.id"))
    key:     Mapped[str]      = mapped_column(String(50))    # e.g. "cuisine", "spice_level"
    value:   Mapped[str]      = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="preferences")

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_pref_key"),
    )


# ═══════════════════════════════════════════════════════════════
# RECIPE DOMAIN
# ═══════════════════════════════════════════════════════════════

class Recipe(Base):
    __tablename__ = "recipes"

    id:           Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    name:         Mapped[str]      = mapped_column(String(200))
    cuisine:      Mapped[str|None] = mapped_column(String(50), nullable=True)
    meal_type:    Mapped[str|None] = mapped_column(String(20), nullable=True)    # breakfast/lunch/dinner/snack
    source:       Mapped[str]      = mapped_column(String(20), default="generated")  # generated / manual / image
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    prep_time_minutes: Mapped[int|None] = mapped_column(Integer, nullable=True)

    # Relationships
    ingredients: Mapped[list[RecipeIngredient]] = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    nutrition:   Mapped[RecipeNutrition | None]  = relationship("RecipeNutrition",  back_populates="recipe", uselist=False, cascade="all, delete-orphan")
    feedback:    Mapped[list[UserFeedback]]      = relationship("UserFeedback",     back_populates="recipe")
    meal_logs:   Mapped[list[MealLog]]           = relationship("MealLog",          back_populates="recipe")

    __table_args__ = (
        Index("ix_recipes_cuisine_meal", "cuisine", "meal_type"),
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id:         Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    recipe_id:  Mapped[str]      = mapped_column(String(36), ForeignKey("recipes.id"))
    name:       Mapped[str]      = mapped_column(String(100))
    quantity:   Mapped[str]      = mapped_column(String(50))

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="ingredients")


class RecipeNutrition(Base):
    __tablename__ = "recipe_nutrition"

    id:         Mapped[str]        = mapped_column(String(36), primary_key=True, default=_uuid)
    recipe_id:  Mapped[str]        = mapped_column(String(36), ForeignKey("recipes.id"), unique=True)
    calories:   Mapped[int]        = mapped_column(Integer)
    protein_g:  Mapped[float]      = mapped_column(Float)
    carbs_g:    Mapped[float]      = mapped_column(Float)
    fat_g:      Mapped[float]      = mapped_column(Float)
    fiber_g:    Mapped[float|None] = mapped_column(Float, nullable=True)
    sodium_mg:  Mapped[float|None] = mapped_column(Float, nullable=True)
    calcium_mg: Mapped[float|None] = mapped_column(Float, nullable=True)
    iron_mg:    Mapped[float|None] = mapped_column(Float, nullable=True)
    sugar_g:    Mapped[float|None] = mapped_column(Float, nullable=True)

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="nutrition")


# ═══════════════════════════════════════════════════════════════
# MEAL PLAN DOMAIN
# ═══════════════════════════════════════════════════════════════

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id:         Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id:    Mapped[str]      = mapped_column(String(36), ForeignKey("users.id"))
    week_start: Mapped[date]     = mapped_column(Date)
    status:     Mapped[str]      = mapped_column(String(20), default="active")   # active / archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user:  Mapped[User]              = relationship("User",         back_populates="meal_plans")
    items: Mapped[list[MealPlanItem]] = relationship("MealPlanItem", back_populates="meal_plan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_meal_plans_user_week", "user_id", "week_start"),
    )


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id:          Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    plan_id:     Mapped[str]      = mapped_column(String(36), ForeignKey("meal_plans.id"))
    recipe_id:   Mapped[str]      = mapped_column(String(36), ForeignKey("recipes.id"))
    day_of_week: Mapped[str]      = mapped_column(String(10))     # Monday…Sunday
    meal_slot:   Mapped[str]      = mapped_column(String(15))     # breakfast/lunch/dinner/snack

    meal_plan: Mapped[MealPlan] = relationship("MealPlan", back_populates="items")
    recipe:    Mapped[Recipe]   = relationship("Recipe")


# ═══════════════════════════════════════════════════════════════
# FEEDBACK & LOGGING
# ═══════════════════════════════════════════════════════════════

class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id:         Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id:    Mapped[str]      = mapped_column(String(36), ForeignKey("users.id"))
    recipe_id:  Mapped[str]      = mapped_column(String(36), ForeignKey("recipes.id"))
    rating:     Mapped[int]      = mapped_column(Integer)        # 1–5
    comment:    Mapped[str|None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user:   Mapped[User]   = relationship("User",   back_populates="feedback")
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="feedback")


class MealLog(Base):
    """Actual meals consumed — may or may not be from a meal plan."""
    __tablename__ = "meal_logs"

    id:                 Mapped[str]        = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id:            Mapped[str]        = mapped_column(String(36), ForeignKey("users.id"))
    recipe_id:          Mapped[str|None]   = mapped_column(String(36), ForeignKey("recipes.id"), nullable=True)
    log_date:           Mapped[date]       = mapped_column(Date)
    meal_slot:          Mapped[str]        = mapped_column(String(15))
    dish_name:          Mapped[str]        = mapped_column(String(200))
    planned:            Mapped[bool]       = mapped_column(Boolean, default=False)
    portion_multiplier: Mapped[float]      = mapped_column(Float, default=1.0)
    calories:           Mapped[int]        = mapped_column(Integer)
    protein_g:          Mapped[float]      = mapped_column(Float)
    carbs_g:            Mapped[float]      = mapped_column(Float)
    fat_g:              Mapped[float]      = mapped_column(Float)
    source:             Mapped[str]        = mapped_column(String(20), default="manual")  # manual/image/plan
    logged_at:          Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)

    user:   Mapped[User]         = relationship("User",   back_populates="meal_logs")
    recipe: Mapped[Recipe|None]  = relationship("Recipe", back_populates="meal_logs")

    __table_args__ = (
        Index("ix_meal_logs_user_date", "user_id", "log_date"),
    )


# ═══════════════════════════════════════════════════════════════
# LEARNING
# ═══════════════════════════════════════════════════════════════

class LearnedPreference(Base):
    """
    Key/value preference store updated by learning_loop_agent.
    Examples:
      key="liked_ingredients"  value="chicken, brown rice"
      key="disliked_ingredients" value="tofu"
      key="spice_preference"   value="high"
      key="goal_refinement"    value="focus on lean bulk, not dirty bulk"
    """
    __tablename__ = "learned_preferences"

    id:         Mapped[str]        = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id:    Mapped[str]        = mapped_column(String(36), ForeignKey("users.id"))
    key:        Mapped[str]        = mapped_column(String(50))
    value:      Mapped[str]        = mapped_column(Text)
    confidence: Mapped[float]      = mapped_column(Float, default=1.0)     # 0.0–1.0
    updated_at: Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="learned_preferences")

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_learned_pref_key"),
    )