"""
weekly_graph_builder.py — Phase 4

Phase 4 upgrade: PostgresSaver checkpointer (same pattern as graph_builder.py).
Weekly plans are long-running — checkpointing means a crash mid-week
won't lose the work already done.

FIX (Phase 4 bug):
  Same issue as graph_builder.py — the original code used a `with` block that
  closes the psycopg connection on exit, leaving a dead connection in the graph.
  Fixed by opening a persistent connection (not a context manager).
"""

import logging
import os

from langgraph.graph import StateGraph, END
from state import WeeklyPlanState

from agents.weekly_plan_agent import weekly_plan_agent_node
from agents.grocery_agent     import grocery_agent_node
from agents.meal_prep_agent   import meal_prep_agent_node

logger = logging.getLogger(__name__)

DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/nutrition_ai",
)


def route_after_plan(state: WeeklyPlanState) -> str:
    if state.pipeline_error:
        return END
    return "grocery_agent"


builder = StateGraph(WeeklyPlanState)
builder.add_node("weekly_plan_agent", weekly_plan_agent_node)
builder.add_node("grocery_agent",     grocery_agent_node)
builder.add_node("meal_prep_agent",   meal_prep_agent_node)

builder.set_entry_point("weekly_plan_agent")
builder.add_conditional_edges(
    "weekly_plan_agent",
    route_after_plan,
    {"grocery_agent": "grocery_agent", END: END}
)
builder.add_edge("grocery_agent",   "meal_prep_agent")
builder.add_edge("meal_prep_agent", END)


def _build_checkpointer():
    """
    Returns a live checkpointer backed by PostgreSQL, or MemorySaver as fallback.

    KEY FIX: We open the psycopg connection directly (NOT inside a `with` block).
    Using `with PostgresSaver.from_conn_string(...) as cp` closes the connection
    the moment the `with` block exits, leaving a dead connection inside the
    compiled graph.  Opening it explicitly keeps it alive for the process lifetime.
    """
    from langgraph.checkpoint.memory import MemorySaver

    # ── Try ConnectionPool first (best for production / concurrent use) ───────
    try:
        from psycopg_pool import ConnectionPool
        from langgraph.checkpoint.postgres import PostgresSaver

        pool = ConnectionPool(
            DB_URI,
            max_size=10,
            kwargs={"autocommit": True},
            open=True,
        )
        cp = PostgresSaver(pool)
        cp.setup()
        logger.info("✅ Weekly graph — PostgresSaver with ConnectionPool ready.")
        return cp
    except ImportError:
        logger.debug("psycopg_pool not installed — trying plain connection.")
    except Exception as e:
        logger.warning("ConnectionPool failed (%s) — trying plain connection.", e)

    # ── Fallback: plain persistent psycopg3 connection ────────────────────────
    try:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver

        # DO NOT use `with psycopg.connect(...)` here — that would close the
        # connection when the block exits.  We want it to stay open.
        conn = psycopg.connect(DB_URI, autocommit=True)
        cp = PostgresSaver(conn)
        cp.setup()
        logger.info("✅ Weekly graph — PostgresSaver with persistent connection ready.")
        return cp
    except Exception as e:
        logger.warning("PostgresSaver failed (%s) — falling back to MemorySaver.", e)

    # ── Last resort: in-memory (no persistence) ───────────────────────────────
    logger.warning("⚠️ Weekly graph using MemorySaver — state will NOT persist between runs.")
    return MemorySaver()


weekly_graph = builder.compile(checkpointer=_build_checkpointer())