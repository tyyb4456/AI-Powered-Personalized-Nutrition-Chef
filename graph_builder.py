"""
graph_builder.py — Phase 4

Phase 4 upgrade:
- Compiles graph with PostgresSaver checkpointer so every state transition
  is persisted to the database
- Falls back to MemorySaver if PostgreSQL is unavailable (dev/offline mode)
- thread_id = user's customer_id so each user has an isolated checkpoint history
- interrupted sessions can be resumed via resume_for_user()

FIX (Phase 4 bug):
  Previously used `with PostgresSaver.from_conn_string(...) as cp:` which
  closes the underlying psycopg connection when the `with` block exits.
  By the time graph.invoke() is called the connection is dead → OperationalError.

  Solution: open a plain persistent psycopg connection (not a context manager)
  so it stays alive for the full lifetime of the process / graph object.
  A ConnectionPool is even better for concurrent use, so we prefer that.

Interrupt flow (Phase 4):
  feedback_agent uses interrupt() for human-in-the-loop feedback collection.
  Use invoke_for_user() to start, then resume_for_user() for each interrupt prompt.
  Use get_interrupt_prompt() to check what the graph is waiting for.
"""

import logging
import os

from langgraph.graph import StateGraph, END
from langgraph.types import Command
from state import NutritionState

from agents.profile_agent          import profile_agent_node
from agents.health_agent           import health_goal_agent_node
from agents.recipe_agent           import recipe_generator_node
from agents.nutrition_validator    import nutrition_validation_agent_node, MAX_RETRIES
from agents.substitution_agent     import substitution_agent_node
from agents.explainability_agent   import explainability_agent_node
from agents.feedback_agent         import feedback_agent_node
from agents.learning_loop_agent    import learning_loop_agent_node
from agents.macro_adjustment_agent import macro_adjustment_agent_node

logger = logging.getLogger(__name__)

DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/nutrition_ai",
)


def route_after_validation(state: NutritionState) -> str:
    if state.validation_passed:
        return "substitution_agent"
    if state.retry_count < MAX_RETRIES:
        print(f"   🔁 Routing to macro adjustment (retry {state.retry_count + 1}/{MAX_RETRIES})")
        return "macro_adjustment_agent"
    print(f"   ⚠️ Max retries reached. Accepting best-effort recipe.")
    return "substitution_agent"


# ── Build graph ───────────────────────────────────────────────────────────────
builder = StateGraph(NutritionState)

builder.add_node("profile_agent",          profile_agent_node)
builder.add_node("health_goal_agent",      health_goal_agent_node)
builder.add_node("recipe_generator",       recipe_generator_node)
builder.add_node("nutrition_validator",    nutrition_validation_agent_node)
builder.add_node("macro_adjustment_agent", macro_adjustment_agent_node)
builder.add_node("substitution_agent",     substitution_agent_node)
builder.add_node("explainability_agent",   explainability_agent_node)
builder.add_node("feedback_agent",         feedback_agent_node)
builder.add_node("learning_loop_agent",    learning_loop_agent_node)

builder.set_entry_point("profile_agent")
builder.add_edge("profile_agent",     "health_goal_agent")
builder.add_edge("health_goal_agent", "recipe_generator")
builder.add_edge("recipe_generator",  "nutrition_validator")

builder.add_conditional_edges(
    "nutrition_validator",
    route_after_validation,
    {
        "macro_adjustment_agent": "macro_adjustment_agent",
        "substitution_agent":     "substitution_agent",
    }
)

builder.add_edge("macro_adjustment_agent", "nutrition_validator")
builder.add_edge("substitution_agent",     "explainability_agent")
builder.add_edge("explainability_agent",   "feedback_agent")
builder.add_edge("feedback_agent",         "learning_loop_agent")
builder.add_edge("learning_loop_agent",    END)


# ── Checkpointer factory ──────────────────────────────────────────────────────

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
            open=True,          # open pool immediately so errors surface here
        )
        cp = PostgresSaver(pool)
        cp.setup()
        logger.info("✅ PostgresSaver with ConnectionPool ready.")
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
        # connection when the block exits. We want it to stay open.
        conn = psycopg.connect(DB_URI, autocommit=True)
        cp = PostgresSaver(conn)
        cp.setup()
        logger.info("✅ PostgresSaver with persistent connection ready.")
        return cp
    except Exception as e:
        logger.warning("PostgresSaver failed (%s) — falling back to MemorySaver.", e)

    # ── Last resort: in-memory (no persistence) ───────────────────────────────
    logger.warning("⚠️ Using MemorySaver — state will NOT persist between runs.")
    return MemorySaver()


# ── Compile once at import time ───────────────────────────────────────────────
graph = builder.compile(checkpointer=_build_checkpointer())


# ── Helper: start graph with user-scoped thread ───────────────────────────────

def invoke_for_user(user_id: str, initial_state: NutritionState | None = None) -> dict:
    """
    Start or resume the graph with a thread_id tied to the user.

    - Pass a NutritionState to start a fresh run.
    - Pass initial_state=None to resume from the last saved checkpoint
      (e.g. after a crash, but NOT for interrupt resumption — use resume_for_user() for that).

    Returns the graph output dict, or an interrupted GraphInterrupt if the
    graph pauses at a feedback_agent interrupt().
    """
    config = {"configurable": {"thread_id": user_id}}
    return graph.invoke(initial_state, config=config)


# ── Helper: resume an interrupted graph ──────────────────────────────────────

def resume_for_user(user_id: str, resume_value) -> dict:
    """
    Resume a graph that is currently paused at an interrupt().

    Call this once per interrupt prompt with the user's answer.
    The graph will run until the next interrupt() or until it reaches END.

    Args:
        user_id:      The same user_id used in invoke_for_user().
        resume_value: The user's answer to the current interrupt prompt
                      (string, int, etc.).

    Returns:
        Graph output dict, or raises GraphInterrupt if another interrupt follows.

    Example usage:
        # Graph paused at "Rate the recipe (1–5):"
        resume_for_user(user_id, "4")

        # Graph paused at "Any comments or suggestions?"
        resume_for_user(user_id, "Loved it!")

        # Graph runs to END
    """
    config = {"configurable": {"thread_id": user_id}}
    return graph.invoke(Command(resume=resume_value), config=config)


# ── Helper: inspect current interrupt prompt ─────────────────────────────────

def get_interrupt_prompt(user_id: str) -> str | None:
    """
    Check whether the graph is currently paused at an interrupt() for this user.

    Returns the interrupt prompt string if the graph is waiting for input,
    or None if the graph is not interrupted (still running or already finished).

    Example usage:
        prompt = get_interrupt_prompt(user_id)
        if prompt:
            user_answer = input(f"{prompt} ")
            resume_for_user(user_id, user_answer)
    """
    config = {"configurable": {"thread_id": user_id}}
    state = graph.get_state(config)

    if state.tasks:
        for task in state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                return task.interrupts[0].value  # the prompt string passed to interrupt()

    return None


# ── Helper: check if graph is done ───────────────────────────────────────────

def is_graph_finished(user_id: str) -> bool:
    """
    Returns True if the graph has reached END for this user's thread,
    False if it is still running or paused at an interrupt.
    """
    config = {"configurable": {"thread_id": user_id}}
    state = graph.get_state(config)
    return len(state.next) == 0