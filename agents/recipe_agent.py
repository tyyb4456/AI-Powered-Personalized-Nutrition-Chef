"""
agents/recipe_agent.py

Generates a personalized recipe using an LLM with STRUCTURED OUTPUT.

Key changes from original:
- LLM is forced to return a RecipeOutput Pydantic model (no free-text parsing)
- Nutrition data is embedded in the structured output — immediately usable
  by the validator without a second parsing step
- Returns only keys this agent modifies
"""

from state import NutritionState
from schemas.nutrition_schemas import RecipeOutput, Ingredient, NutritionFacts
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")

# Force the LLM to return a RecipeOutput Pydantic model
model = model.with_structured_output(RecipeOutput)

# ── Prompt ────────────────────────────────────────────────────────────────────
RECIPE_PROMPT = ChatPromptTemplate.from_template("""
You are a world-class AI chef and certified nutritionist.

Create a personalized, health-optimized meal for this customer:

👤 Profile:
- Age: {age}
- Fitness Goal: {fitness_goal}
- Calorie Target: {calorie_target} kcal
- Macro Split — Protein: {protein_pct}% | Carbs: {carbs_pct}% | Fat: {fat_pct}%
- Preferences: {preferences}
- Allergies / Restrictions: {allergies}

🎯 Requirements:
1. Total calories must be as close to {calorie_target} kcal as possible (within ±10%)
2. Macro ratios must match the split above (within ±5%)
3. ZERO allergens from the list above — no exceptions
4. Reflect the cuisine and spice preferences
5. Use accessible ingredients, realistic steps for a home cook

Return a complete recipe with: dish name, all ingredients with quantities,
step-by-step instructions, and precise nutritional breakdown.
""")


def recipe_generator_node(state: NutritionState) -> dict:
    print("\n🍽️ Generating personalized recipe...")

    macro = state.macro_split

    messages = RECIPE_PROMPT.format_messages(
        age=state.age or "not specified",
        fitness_goal=state.fitness_goal or "maintenance",
        calorie_target=state.calorie_target,
        protein_pct=macro.protein,
        carbs_pct=macro.carbs,
        fat_pct=macro.fat,
        preferences=state.preferences or "no specific preferences",
        allergies=state.allergies or "none",
    )

    # LLM returns a validated RecipeOutput object — no parsing needed
    recipe: RecipeOutput = model.invoke(messages)

    print(f"✅ Recipe generated: '{recipe.dish_name}'")
    print(f"   Nutrition → {recipe.nutrition.calories} kcal | "
          f"P: {recipe.nutrition.protein_g}g | "
          f"C: {recipe.nutrition.carbs_g}g | "
          f"F: {recipe.nutrition.fat_g}g")

    return {
        "generated_recipe": recipe,
        "recipe_generated":  True,
    }