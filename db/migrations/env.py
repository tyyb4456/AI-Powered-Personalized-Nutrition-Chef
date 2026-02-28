"""
db/migrations/env.py

Alembic migration environment.
Run migrations with:
  alembic upgrade head         # apply all pending migrations
  alembic revision --autogenerate -m "description"   # generate new migration
  alembic downgrade -1         # roll back one step
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make project root importable ──────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from db.models import Base

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment variable
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:tybpost%%40%%2356*@localhost:5432/nutrition_ai",
)
# Bypass configparser interpolation entirely
from alembic.config import Config
config.attributes["sqlalchemy.url"] = database_url

target_metadata = Base.metadata


# ── Offline mode (generates SQL without connecting) ───────────────────────────

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connects and applies migrations) ─────────────────────────────

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,        # detect column type changes
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()