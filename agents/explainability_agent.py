"""
agents/explainability_agent.py

Phase 2: explanation now includes age-specific and medical condition reasoning.
"""

from state import NutritionState
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")

EXPLANATION_PROMPT = ChatPromptTemplate.from_template("""
You are an AI Nutrition Assistant. Explain this meal choice to the customer
in friendly, science-backed language.

🧑‍🍳 Customer Profile:
- Name: {name}
- Age: {age} ({age_group})
- Fitness Goal: {fitness_goal}
- Calorie Target: {calorie_target} kcal
- Macro Split: Protein {protein_pct}% | Carbs {carbs_pct}% | Fat {fat_pct}%
- Preferences: {preferences}
- Allergies: {allergies}
- Medical Conditions: {medical_conditions}
- Substitutions made: {substitutions_made}

🍽️ Final Recipe: {dish_name}
Ingredients: {ingredients}
Nutrition: {calories} kcal | Protein {protein}g | Carbs {carbs}g | Fat {fat}g | Fiber {fiber}g

✅ Cover in your explanation:
1. How this recipe supports their specific fitness goal
2. Why the calorie and macro balance is appropriate for their age and profile
3. How their preferences and allergen restrictions were respected
4. Any age-specific or medical benefits of this meal (e.g. high calcium for seniors)
5. The reason for any ingredient substitutions (if any were made)
6. Why this is a smart, personalized choice overall

Keep tone friendly, professional, and easy to understand — like talking to a health-conscious friend.
""")


def explainability_agent_node(state: NutritionState) -> dict:
    print("\n🧠 Generating recipe explanation...")

    recipe = state.final_recipe
    if recipe is None:
        return {"recipe_explanation": "No recipe available to explain."}

    macro        = state.macro_split
    nutrition    = recipe.nutrition
    age_profile  = state.age_profile
    conditions_str = (
        ", ".join(c.condition for c in state.medical_conditions)
        if state.medical_conditions else "none"
    )
    ingredients_text = ", ".join(f"{ing.quantity} {ing.name}" for ing in recipe.ingredients)

    messages = EXPLANATION_PROMPT.format_messages(
        name=state.name or "there",
        age=state.age or "not specified",
        age_group=age_profile.age_group if age_profile else "adult",
        fitness_goal=state.fitness_goal,
        calorie_target=state.calorie_target,
        protein_pct=macro.protein,
        carbs_pct=macro.carbs,
        fat_pct=macro.fat,
        preferences=state.preferences or "none",
        allergies=", ".join(state.allergies) if state.allergies else "none",
        medical_conditions=conditions_str,
        substitutions_made=state.substitutions_made,
        dish_name=recipe.dish_name,
        ingredients=ingredients_text,
        calories=nutrition.calories,
        protein=nutrition.protein_g,
        carbs=nutrition.carbs_g,
        fat=nutrition.fat_g,
        fiber=nutrition.fiber_g or "not reported",
    )

    response = model.invoke(messages)
    return {"recipe_explanation": response.content}