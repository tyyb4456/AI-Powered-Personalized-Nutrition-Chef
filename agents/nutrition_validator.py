from state import NutritionState

def nutrition_validation_agent_node(state: NutritionState) -> NutritionState:
    print("\n✅ Validating nutritional alignment...")

    # Simple validation logic for now
    # You can replace with a more detailed nutrition model or fuzzy logic later
    target = state.calorie_target
    estimated = state.recipe_nutrition.get("estimated_calories", 0)

    diff = abs(target - estimated)
    passes = diff <= 200  # ±200 kcal buffer allowed

    notes = (
        f"Recipe matches target. Target: {target} kcal, Estimated: {estimated} kcal"
        if passes
        else f"⚠️ Recipe is off by {diff} kcal. Consider regenerating or adjusting ingredients."
    )
    state = {
        "validation_passed": passes,
        "validation_notes": notes
    }

    return state
