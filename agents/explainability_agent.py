"""
agents/explainability_agent.py

Explains why this specific recipe was chosen for this specific user.

Key changes from original:
- Uses state.final_recipe (the definitive final recipe) instead of
  manually checking revised_recipe vs generated_recipe
- Still uses free text output here — explanation is meant to be
  human-readable prose, not structured data
- Returns only keys this agent modifies
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
- Fitness Goal: {fitness_goal}
- Calorie Target: {calorie_target} kcal
- Macro Split: Protein {protein_pct}% | Carbs {carbs_pct}% | Fat {fat_pct}%
- Preferences: {preferences}
- Allergies: {allergies}
- Substitutions made: {substitutions_made}

🍽️ Final Recipe: {dish_name}
Ingredients: {ingredients}
Nutrition: {calories} kcal | Protein {protein}g | Carbs {carbs}g | Fat {fat}g

✅ Cover in your explanation:
1. How this recipe supports their fitness goal
2. Why the calorie and macro balance is appropriate for them
3. How their preferences and allergen restrictions were respected
4. The reason for any ingredient substitutions (if any were made)
5. Why this is a smart, personalized choice overall

Keep tone friendly, professional, and easy to understand.
""")


def explainability_agent_node(state: NutritionState) -> dict:
    print("\n🧠 Generating recipe explanation...")

    recipe = state.final_recipe
    if recipe is None:
        return {"recipe_explanation": "No recipe available to explain."}

    macro = state.macro_split
    nutrition = recipe.nutrition
    ingredients_text = ", ".join(
        f"{ing.quantity} {ing.name}" for ing in recipe.ingredients
    )

    messages = EXPLANATION_PROMPT.format_messages(
        fitness_goal=state.fitness_goal,
        calorie_target=state.calorie_target,
        protein_pct=macro.protein,
        carbs_pct=macro.carbs,
        fat_pct=macro.fat,
        preferences=state.preferences or "none",
        allergies=state.allergies or "none",
        substitutions_made=state.substitutions_made,
        dish_name=recipe.dish_name,
        ingredients=ingredients_text,
        calories=nutrition.calories,
        protein=nutrition.protein_g,
        carbs=nutrition.carbs_g,
        fat=nutrition.fat_g,
    )

    response = model.invoke(messages)
    print(response)

    return {"recipe_explanation": response.content}