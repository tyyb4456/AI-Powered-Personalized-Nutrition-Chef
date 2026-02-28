"""
graph_builder.py — Phase 4

Phase 4 upgrade:
- Compiles graph with PostgresSaver checkpointer so every state transition
  is persisted to the database
- Falls back to MemorySaver if PostgreSQL is unavailable (dev/offline mode)
- thread_id = user's customer_id so each user has an isolated checkpoint history
- interrupted sessions can be resumed: graph.invoke(None, config={"configurable":{"thread_id": user_id}})
"""

import logging
import os

from langgraph.graph import StateGraph, END
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


import os
import logging
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

logger = logging.getLogger(__name__)

DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/nutrition_ai",
)

def build_graph(builder):
    try:
        with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
            checkpointer.setup()  # create tables (run once)

            logger.info("✅ Using PostgresSaver")

            return builder.compile(checkpointer=checkpointer)

    except Exception as e:
        logger.warning("PostgresSaver failed: %s", e)
        logger.warning("⚠️ Falling back to MemorySaver")

        return builder.compile(checkpointer=MemorySaver())


graph = build_graph(builder)


# ── Helper: invoke with user-scoped thread ────────────────────────────────────

def invoke_for_user(user_id: str, initial_state: NutritionState | None = None) -> dict:
    """
    Invoke the graph with a thread_id tied to the user.
    If the user has a saved checkpoint, LangGraph resumes from the last state.
    Pass initial_state=None to resume; pass a NutritionState to start fresh.
    """
    config = {"configurable": {"thread_id": user_id}}
    input_state = initial_state if initial_state is not None else None
    return graph.invoke(input_state, config=config)