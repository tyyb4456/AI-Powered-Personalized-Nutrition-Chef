"""
db/migrations/versions/001_initial_schema.py

Initial migration — creates all tables.

Generate future migrations with:
  alembic revision --autogenerate -m "your description"
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",         sa.String(36),  primary_key=True),
        sa.Column("name",       sa.String(100), nullable=False),
        sa.Column("email",      sa.String(255), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime,    nullable=False),
        sa.Column("updated_at", sa.DateTime,    nullable=False),
    )

    # ── user_profiles ─────────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id",             sa.String(36),  primary_key=True),
        sa.Column("user_id",        sa.String(36),  sa.ForeignKey("users.id"), unique=True),
        sa.Column("age",            sa.Integer,     nullable=True),
        sa.Column("gender",         sa.String(10),  nullable=True),
        sa.Column("weight_kg",      sa.Float,       nullable=True),
        sa.Column("height_cm",      sa.Float,       nullable=True),
        sa.Column("activity_level", sa.String(20),  nullable=True),
        sa.Column("updated_at",     sa.DateTime,    nullable=False),
    )

    # ── user_goals ────────────────────────────────────────────────────────────
    op.create_table(
        "user_goals",
        sa.Column("id",             sa.String(36), primary_key=True),
        sa.Column("user_id",        sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("goal_type",      sa.String(30), nullable=False),
        sa.Column("calorie_target", sa.Integer,    nullable=False),
        sa.Column("protein_pct",    sa.Integer,    nullable=False),
        sa.Column("carbs_pct",      sa.Integer,    nullable=False),
        sa.Column("fat_pct",        sa.Integer,    nullable=False),
        sa.Column("set_at",         sa.DateTime,   nullable=False),
    )
    op.create_index("ix_user_goals_user_set", "user_goals", ["user_id", "set_at"])

    # ── medical_conditions ────────────────────────────────────────────────────
    op.create_table(
        "medical_conditions",
        sa.Column("id",        sa.String(36), primary_key=True),
        sa.Column("user_id",   sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("condition", sa.String(50), nullable=False),
        sa.Column("notes",     sa.Text,       nullable=True),
        sa.Column("added_at",  sa.DateTime,   nullable=False),
        sa.UniqueConstraint("user_id", "condition", name="uq_user_condition"),
    )

    # ── user_allergies ────────────────────────────────────────────────────────
    op.create_table(
        "user_allergies",
        sa.Column("id",       sa.String(36),  primary_key=True),
        sa.Column("user_id",  sa.String(36),  sa.ForeignKey("users.id")),
        sa.Column("allergen", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20),  nullable=True),
        sa.UniqueConstraint("user_id", "allergen", name="uq_user_allergen"),
    )

    # ── user_preferences ──────────────────────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("user_id",    sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("key",        sa.String(50), nullable=False),
        sa.Column("value",      sa.Text,       nullable=False),
        sa.Column("updated_at", sa.DateTime,   nullable=False),
        sa.UniqueConstraint("user_id", "key", name="uq_user_pref_key"),
    )

    # ── recipes ───────────────────────────────────────────────────────────────
    op.create_table(
        "recipes",
        sa.Column("id",                  sa.String(36),  primary_key=True),
        sa.Column("name",                sa.String(200), nullable=False),
        sa.Column("cuisine",             sa.String(50),  nullable=True),
        sa.Column("meal_type",           sa.String(20),  nullable=True),
        sa.Column("source",              sa.String(20),  nullable=False, server_default="generated"),
        sa.Column("generated_at",        sa.DateTime,    nullable=False),
        sa.Column("prep_time_minutes",   sa.Integer,     nullable=True),
    )
    op.create_index("ix_recipes_cuisine_meal", "recipes", ["cuisine", "meal_type"])

    # ── recipe_ingredients ────────────────────────────────────────────────────
    op.create_table(
        "recipe_ingredients",
        sa.Column("id",        sa.String(36),  primary_key=True),
        sa.Column("recipe_id", sa.String(36),  sa.ForeignKey("recipes.id")),
        sa.Column("name",      sa.String(100), nullable=False),
        sa.Column("quantity",  sa.String(50),  nullable=False),
    )

    # ── recipe_nutrition ──────────────────────────────────────────────────────
    op.create_table(
        "recipe_nutrition",
        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("recipe_id",  sa.String(36), sa.ForeignKey("recipes.id"), unique=True),
        sa.Column("calories",   sa.Integer,    nullable=False),
        sa.Column("protein_g",  sa.Float,      nullable=False),
        sa.Column("carbs_g",    sa.Float,      nullable=False),
        sa.Column("fat_g",      sa.Float,      nullable=False),
        sa.Column("fiber_g",    sa.Float,      nullable=True),
        sa.Column("sodium_mg",  sa.Float,      nullable=True),
        sa.Column("calcium_mg", sa.Float,      nullable=True),
        sa.Column("iron_mg",    sa.Float,      nullable=True),
        sa.Column("sugar_g",    sa.Float,      nullable=True),
    )

    # ── meal_plans ────────────────────────────────────────────────────────────
    op.create_table(
        "meal_plans",
        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("user_id",    sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("week_start", sa.Date,       nullable=False),
        sa.Column("status",     sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime,   nullable=False),
    )
    op.create_index("ix_meal_plans_user_week", "meal_plans", ["user_id", "week_start"])

    # ── meal_plan_items ───────────────────────────────────────────────────────
    op.create_table(
        "meal_plan_items",
        sa.Column("id",          sa.String(36), primary_key=True),
        sa.Column("plan_id",     sa.String(36), sa.ForeignKey("meal_plans.id")),
        sa.Column("recipe_id",   sa.String(36), sa.ForeignKey("recipes.id")),
        sa.Column("day_of_week", sa.String(10), nullable=False),
        sa.Column("meal_slot",   sa.String(15), nullable=False),
    )

    # ── user_feedback ─────────────────────────────────────────────────────────
    op.create_table(
        "user_feedback",
        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("user_id",    sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("recipe_id",  sa.String(36), sa.ForeignKey("recipes.id")),
        sa.Column("rating",     sa.Integer,    nullable=False),
        sa.Column("comment",    sa.Text,       nullable=True),
        sa.Column("created_at", sa.DateTime,   nullable=False),
    )

    # ── meal_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "meal_logs",
        sa.Column("id",                 sa.String(36),  primary_key=True),
        sa.Column("user_id",            sa.String(36),  sa.ForeignKey("users.id")),
        sa.Column("recipe_id",          sa.String(36),  sa.ForeignKey("recipes.id"), nullable=True),
        sa.Column("log_date",           sa.Date,        nullable=False),
        sa.Column("meal_slot",          sa.String(15),  nullable=False),
        sa.Column("dish_name",          sa.String(200), nullable=False),
        sa.Column("planned",            sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("portion_multiplier", sa.Float,       nullable=False, server_default="1.0"),
        sa.Column("calories",           sa.Integer,     nullable=False),
        sa.Column("protein_g",          sa.Float,       nullable=False),
        sa.Column("carbs_g",            sa.Float,       nullable=False),
        sa.Column("fat_g",              sa.Float,       nullable=False),
        sa.Column("source",             sa.String(20),  nullable=False, server_default="manual"),
        sa.Column("logged_at",          sa.DateTime,    nullable=False),
    )
    op.create_index("ix_meal_logs_user_date", "meal_logs", ["user_id", "log_date"])

    # ── learned_preferences ───────────────────────────────────────────────────
    op.create_table(
        "learned_preferences",
        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("user_id",    sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("key",        sa.String(50), nullable=False),
        sa.Column("value",      sa.Text,       nullable=False),
        sa.Column("confidence", sa.Float,      nullable=False, server_default="1.0"),
        sa.Column("updated_at", sa.DateTime,   nullable=False),
        sa.UniqueConstraint("user_id", "key", name="uq_learned_pref_key"),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("learned_preferences")
    op.drop_table("meal_logs")
    op.drop_table("user_feedback")
    op.drop_table("meal_plan_items")
    op.drop_table("meal_plans")
    op.drop_table("recipe_nutrition")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
    op.drop_table("user_preferences")
    op.drop_table("user_allergies")
    op.drop_table("medical_conditions")
    op.drop_table("user_goals")
    op.drop_table("user_profiles")
    op.drop_table("users")