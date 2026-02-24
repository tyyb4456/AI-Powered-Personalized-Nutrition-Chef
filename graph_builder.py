from langgraph.graph import StateGraph, END
from state import NutritionState
from agents.profile_agent import profile_agent_node
from agents.health_agent import health_goal_agent_node  
from agents.recipe_agent import recipe_generator_node  
from agents.nutrition_validator import nutrition_validation_agent_node  
from agents.substitution_agent import substitution_agent_node  
from agents.explainability_agent import explainability_agent_node  
from agents.feedback_agent import feedback_agent_node  
from agents.learning_loop_agent import learning_loop_agent_node  
from agents.macro_adjustment_agent import macro_adjustment_agent_node 

# Build graph
builder = StateGraph(NutritionState)

# Register nodes
# Add all nodes
builder.add_node("profile_agent", profile_agent_node)
builder.add_node("health_goal_agent", health_goal_agent_node)
builder.add_node("recipe_generator", recipe_generator_node)
builder.add_node("nutrition_validator", nutrition_validation_agent_node)
builder.add_node("macro_adjustment_agent", macro_adjustment_agent_node) 
builder.add_node("substitution_agent", substitution_agent_node)
builder.add_node("explainability_agent", explainability_agent_node)
builder.add_node("feedback_agent", feedback_agent_node)
builder.add_node("learning_loop_agent", learning_loop_agent_node)

# Entry
builder.set_entry_point("profile_agent")

# Static edges
builder.add_edge("profile_agent", "health_goal_agent")
builder.add_edge("health_goal_agent", "recipe_generator")
builder.add_edge("recipe_generator", "nutrition_validator")

# Conditional & reroute edges
builder.add_conditional_edges(
    "nutrition_validator",
    lambda state: (
        "substitution_agent" if state.validation_passed else "macro_adjustment_agent"
    )
)
builder.add_edge("macro_adjustment_agent", "nutrition_validator")


builder.add_edge("substitution_agent", "explainability_agent")
builder.add_edge("explainability_agent", "feedback_agent")
builder.add_edge("feedback_agent", "learning_loop_agent")
builder.add_edge("learning_loop_agent", END)




# Compile
graph = builder.compile()