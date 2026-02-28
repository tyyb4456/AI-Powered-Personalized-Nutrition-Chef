"""
weekly_graph_builder.py — Phase 4

Phase 4 upgrade: PostgresSaver checkpointer (same pattern as graph_builder.py).
Weekly plans are long-running — checkpointing means a crash mid-week
won't lose the work already done.
"""

import logging
import os

from langgraph.graph import StateGraph, END
from state import WeeklyPlanState

from agents.weekly_plan_agent import weekly_plan_agent_node
from agents.grocery_agent     import grocery_agent_node
from agents.meal_prep_agent   import meal_prep_agent_node

logger = logging.getLogger(__name__)


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
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/nutrition_ai",
    )
    try:
        from langgraph.checkpoint.memory import PostgresSaver
        cp = PostgresSaver.from_conn_string(database_url)
        cp.setup()
        logger.info("✅ Weekly graph checkpointer: PostgresSaver")
        return cp
    except Exception as e:
        logger.warning("PostgresSaver unavailable (%s). Using MemorySaver.", e)
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()


weekly_graph = builder.compile(checkpointer=_build_checkpointer())