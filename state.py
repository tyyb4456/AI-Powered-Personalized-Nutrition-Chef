from typing import Dict, Any, Optional
from pydantic import BaseModel

class NutritionState(BaseModel):
    customer_id: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    allergies: Optional[list[str]] = []
    preferences: Optional[Dict[str, Any]] = {}
    fitness_goal: Optional[str] = None
    profile_collected: bool = False


    # 🆕 New fields for HealthGoalAgent
    calorie_target: Optional[int] = None
    macro_split: Optional[Dict[str, int]] = None  # e.g., {"protein": 30, "carbs": 40, "fat": 30}
    goal_interpreted: bool = False

    # 🆕 New for RecipeAgent
    generated_recipe: str = ""
    recipe_nutrition: Optional[Dict[str, Any]] = None
    recipe_generated: bool = False

    # 🆕 New for NutritionValidationAgent
    validation_passed: Optional[bool] = None
    validation_notes: Optional[str] = None

    # 🆕 Substitution fields
    substitutions_made: Optional[bool] = False
    revised_recipe: Optional[str] = None

    # 🧠 New for ExplainabilityAgent
    recipe_explanation: Optional[str] = None

    # 🧪 Feedback fields
    feedback_rating: Optional[int] = None  # 1 to 5
    feedback_comment: Optional[str] = None
    feedback_collected: bool = False

    # 🔁 Learning loop memory
    learned_preferences: Optional[Dict[str, Any]] = {}
    updated_goals: Optional[str] = None

    adjusted_by_macro_agent: bool = False  # default
