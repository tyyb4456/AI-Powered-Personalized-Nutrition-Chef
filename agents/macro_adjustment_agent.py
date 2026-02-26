"""
agents/macro_adjustment_agent.py

Adjusts the recipe's macro balance when validation fails.
Phase 2: updated to use gemini-2.5-flash via init_chat_model.
"""

from state import NutritionState
from schemas.nutrition_schemas import MacroAdjustmentOutput
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")
llm   = model.with_structured_output(MacroAdjustmentOutput)

MACRO_PROMPT = ChatPromptTemplate.from_template("""
You are an AI Nutrition Coach and Recipe Optimizer.

The recipe below FAILED nutritional validation. Adjust it to meet the targets.

🎯 Targets:
- Calorie Target: {calorie_target} kcal (must be within ±10%)
- Macro Split: Protein {protein_pct}% | Carbs {carbs_pct}% | Fat {fat_pct}% (each within ±5%)
- Fiber minimum: 5g

❌ Why it failed:
{validation_notes}

🍽️ Current Recipe:
Dish: {dish_name}
Ingredients:
{ingredients}

Steps:
{steps}

Current Nutrition:
- Calories: {actual_calories} kcal
- Protein:  {actual_protein}g
- Carbs:    {actual_carbs}g
- Fat:      {actual_fat}g
- Fiber:    {actual_fiber}g

🚫 Allergens to avoid: {allergies}
⚕️ Medical conditions: {medical_conditions}

Instructions:
- Adjust ingredient quantities or swap ingredients to hit the macro targets
- Keep the dish recognizable — don't completely change it
- Ensure fiber >= 5g
- Recalculate nutrition accurately after adjustments
- Explain what you changed and why in adjustment_notes
""")


def macro_adjustment_agent_node(state: NutritionState) -> dict:
    print(f"\n🛠️ Adjusting macros (attempt {state.retry_count + 1})...")

    if state.macro_adjustment_output:
        recipe = state.macro_adjustment_output.adjusted_recipe
    else:
        recipe = state.generated_recipe

    nutrition = recipe.nutrition
    macro     = state.macro_split

    ingredients_text = "\n".join(f"- {ing.quantity} {ing.name}" for ing in recipe.ingredients)
    steps_text       = "\n".join(f"{i+1}. {step}" for i, step in enumerate(recipe.steps))
    conditions_str   = (
        ", ".join(c.condition for c in state.medical_conditions)
        if state.medical_conditions else "none"
    )

    messages = MACRO_PROMPT.format_messages(
        calorie_target=state.calorie_target,
        protein_pct=macro.protein,
        carbs_pct=macro.carbs,
        fat_pct=macro.fat,
        validation_notes=state.validation_notes or "Unknown failure",
        dish_name=recipe.dish_name,
        ingredients=ingredients_text,
        steps=steps_text,
        actual_calories=nutrition.calories,
        actual_protein=nutrition.protein_g,
        actual_carbs=nutrition.carbs_g,
        actual_fat=nutrition.fat_g,
        actual_fiber=nutrition.fiber_g or "not reported",
        allergies=", ".join(state.allergies) if state.allergies else "none",
        medical_conditions=conditions_str,
    )

    result: MacroAdjustmentOutput = llm.invoke(messages)

    print(f"   Adjusted: '{result.adjusted_recipe.dish_name}'")
    print(f"   Notes: {result.adjustment_notes}")

    return {
        "macro_adjustment_output": result,
        "adjusted_by_macro_agent": True,
        "retry_count":             state.retry_count + 1,
    }