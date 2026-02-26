"""
weekly_graph_builder.py

Separate LangGraph pipeline for the weekly meal planning workflow.

Graph:
  weekly_plan_agent → grocery_agent → meal_prep_agent → END

Progress agent runs separately (standalone mode, not in this graph).
Image agent runs separately (standalone mode).
"""

from langgraph.graph import StateGraph, END
from state import WeeklyPlanState

from agents.weekly_plan_agent import weekly_plan_agent_node
from agents.grocery_agent     import grocery_agent_node
from agents.meal_prep_agent   import meal_prep_agent_node


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
    {
        "grocery_agent": "grocery_agent",
        END:             END,
    }
)

builder.add_edge("grocery_agent",   "meal_prep_agent")
builder.add_edge("meal_prep_agent", END)

weekly_graph = builder.compile()