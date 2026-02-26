"""
agents/substitution_agent.py

Checks for allergen/preference conflicts and substitutes ingredients.

Key changes from original:
- Returns structured SubstitutionOutput instead of raw text
- Uses generated_recipe (RecipeOutput object) correctly
- Determines final_recipe for downstream agents
- Returns only keys this agent modifies
"""

from state import NutritionState
from schemas.nutrition_schemas import SubstitutionOutput
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")

llm = model.with_structured_output(SubstitutionOutput)

# ── Prompt ────────────────────────────────────────────────────────────────────
SUBSTITUTION_PROMPT = ChatPromptTemplate.from_template("""
You are a dietary safety specialist and AI chef.

Review the recipe below for ingredient conflicts with the customer's allergies
and preferences. Make safe substitutions where needed.

⚠️ Allergies (MUST avoid): {allergies}
👅 Taste Preferences / Restrictions: {preferences}

🍽️ Recipe to Review:
Dish: {dish_name}
Ingredients:
{ingredients}

Steps:
{steps}

Nutrition:
- Calories: {calories} kcal | Protein: {protein}g | Carbs: {carbs}g | Fat: {fat}g

Instructions:
- If NO conflicts found: set substitutions_made=false, leave revised_recipe as null
- If conflicts found: set substitutions_made=true, list each substitution with reasoning,
  and provide a complete revised recipe with updated ingredients, steps, and nutrition
- Substitutions must maintain similar calorie/macro balance
- Use realistic, commonly available substitute ingredients
""")


def substitution_agent_node(state: NutritionState) -> dict:
    print("\n🔄 Checking recipe for allergen/preference conflicts...")

    # Use the macro-adjusted recipe if available, else original
    if state.adjusted_by_macro_agent and state.macro_adjustment_output:
        recipe = state.macro_adjustment_output.adjusted_recipe
    else:
        recipe = state.generated_recipe

    nutrition = recipe.nutrition
    ingredients_text = "\n".join(
        f"- {ing.quantity} {ing.name}" for ing in recipe.ingredients
    )
    steps_text = "\n".join(
        f"{i+1}. {step}" for i, step in enumerate(recipe.steps)
    )

    messages = SUBSTITUTION_PROMPT.format_messages(
        allergies=state.allergies or "none",
        preferences=state.preferences or "no specific restrictions",
        dish_name=recipe.dish_name,
        ingredients=ingredients_text,
        steps=steps_text,
        calories=nutrition.calories,
        protein=nutrition.protein_g,
        carbs=nutrition.carbs_g,
        fat=nutrition.fat_g,
    )

    result: SubstitutionOutput = llm.invoke(messages)

    # ── Determine the final recipe ────────────────────────────────────────────
    if result.substitutions_made and result.revised_recipe:
        final_recipe = result.revised_recipe
        print(f"   ✅ {len(result.substitutions)} substitution(s) made.")
        for sub in result.substitutions:
            print(f"      {sub.original_ingredient} → {sub.substitute_ingredient}: {sub.reason}")
    else:
        final_recipe = recipe
        print("   ✅ No conflicts found — recipe is safe as-is.")

    return {
        "substitution_output": result,
        "substitutions_made":  result.substitutions_made,
        "final_recipe":        final_recipe,
    }