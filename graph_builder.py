"""
graph_builder.py

LangGraph pipeline for the Nutrition AI system.

Key changes from original:
- Conditional router for validation uses retry_count to break infinite loops
- MAX_RETRIES cap: after 2 failed macro adjustments, skip to substitution
  (we accept "best effort" rather than looping forever)
- All edges verified against actual agent return keys
"""

from langgraph.graph import StateGraph, END
from state import NutritionState

from agents.profile_agent        import profile_agent_node
from agents.health_agent         import health_goal_agent_node
from agents.recipe_agent         import recipe_generator_node
from agents.nutrition_validator  import nutrition_validation_agent_node, MAX_RETRIES
from agents.substitution_agent   import substitution_agent_node
from agents.explainability_agent import explainability_agent_node
from agents.feedback_agent       import feedback_agent_node
from agents.learning_loop_agent  import learning_loop_agent_node
from agents.macro_adjustment_agent import macro_adjustment_agent_node


# ── Routing function after validation ────────────────────────────────────────
def route_after_validation(state: NutritionState) -> str:
    """
    Decision logic after nutrition_validator runs:

    - Passed → substitution_agent (check allergens, then finalize)
    - Failed AND retries remaining → macro_adjustment_agent
    - Failed AND retries exhausted → substitution_agent anyway
      (accept best-effort recipe, don't loop forever)
    """
    if state.validation_passed:
        return "substitution_agent"

    if state.retry_count < MAX_RETRIES:
        print(f"   🔁 Routing to macro adjustment (retry {state.retry_count + 1}/{MAX_RETRIES})")
        return "macro_adjustment_agent"

    print(f"   ⚠️ Max retries reached ({MAX_RETRIES}). Accepting best-effort recipe.")
    return "substitution_agent"


# ── Build graph ───────────────────────────────────────────────────────────────
builder = StateGraph(NutritionState)

builder.add_node("profile_agent",         profile_agent_node)
builder.add_node("health_goal_agent",     health_goal_agent_node)
builder.add_node("recipe_generator",      recipe_generator_node)
builder.add_node("nutrition_validator",   nutrition_validation_agent_node)
builder.add_node("macro_adjustment_agent", macro_adjustment_agent_node)
builder.add_node("substitution_agent",    substitution_agent_node)
builder.add_node("explainability_agent",  explainability_agent_node)
builder.add_node("feedback_agent",        feedback_agent_node)
builder.add_node("learning_loop_agent",   learning_loop_agent_node)

# ── Entry point ───────────────────────────────────────────────────────────────
builder.set_entry_point("profile_agent")

# ── Static edges ──────────────────────────────────────────────────────────────
builder.add_edge("profile_agent",     "health_goal_agent")
builder.add_edge("health_goal_agent", "recipe_generator")
builder.add_edge("recipe_generator",  "nutrition_validator")

# ── Conditional: after validation ─────────────────────────────────────────────
builder.add_conditional_edges(
    "nutrition_validator",
    route_after_validation,
    {
        "macro_adjustment_agent": "macro_adjustment_agent",
        "substitution_agent":     "substitution_agent",
    }
)

# ── Macro adjustment loops back to validator ──────────────────────────────────
builder.add_edge("macro_adjustment_agent", "nutrition_validator")

# ── Post-validation pipeline ──────────────────────────────────────────────────
builder.add_edge("substitution_agent",    "explainability_agent")
builder.add_edge("explainability_agent",  "feedback_agent")
builder.add_edge("feedback_agent",        "learning_loop_agent")
builder.add_edge("learning_loop_agent",   END)

# ── Compile ───────────────────────────────────────────────────────────────────
graph = builder.compile()