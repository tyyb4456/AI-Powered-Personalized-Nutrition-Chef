"""
agents/health_agent.py

Interprets the user's fitness goal and calculates a science-based
calorie target + macro split using the Mifflin-St Jeor equation.

Returns only the keys it modifies — LangGraph merges the rest.
"""

from state import NutritionState
from schemas.nutrition_schemas import MacroSplit


# ── Activity level multipliers (Mifflin-St Jeor) ─────────────────────────────
ACTIVITY_FACTORS = {
    "sedentary":   1.2,
    "light":       1.375,
    "moderate":    1.55,
    "active":      1.725,
    "very_active": 1.9,
}

# ── Fallback if profile data is missing ──────────────────────────────────────
DEFAULT_CALORIES = {
    "muscle_gain": 2800,
    "fat_loss":    1800,
    "maintenance": 2200,
}

DEFAULT_MACROS = {
    "muscle_gain": MacroSplit(protein=40, carbs=35, fat=25),
    "fat_loss":    MacroSplit(protein=30, carbs=30, fat=40),
    "maintenance": MacroSplit(protein=30, carbs=40, fat=30),
}


def _classify_goal(goal: str) -> str:
    """Map free-text goal to one of three canonical types."""
    goal = goal.lower()
    if any(k in goal for k in ["muscle", "gain", "bulk", "mass"]):
        return "muscle_gain"
    elif any(k in goal for k in ["loss", "cut", "fat", "slim", "lean", "weight"]):
        return "fat_loss"
    return "maintenance"


def _calculate_bmr(age: int, gender: str, weight_kg: float, height_cm: float) -> float:
    """Mifflin-St Jeor BMR equation."""
    if gender.lower() in ("male", "m"):
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def health_goal_agent_node(state: NutritionState) -> dict:
    print("\n💪 Calculating science-based dietary requirements...")

    goal_type = _classify_goal(state.fitness_goal or "")

    # ── Try science-based calculation first ──────────────────────────────────
    calorie_target = None

    if all([state.age, state.gender, state.weight_kg, state.height_cm]):
        try:
            bmr = _calculate_bmr(
                age=state.age,
                gender=state.gender,
                weight_kg=state.weight_kg,
                height_cm=state.height_cm,
            )
            activity = (state.activity_level or "moderate").lower().replace(" ", "_")
            factor = ACTIVITY_FACTORS.get(activity, 1.55)
            tdee = bmr * factor  # Total Daily Energy Expenditure

            # Adjust TDEE based on goal
            if goal_type == "muscle_gain":
                calorie_target = int(tdee + 300)   # lean bulk surplus
            elif goal_type == "fat_loss":
                calorie_target = int(tdee - 500)   # safe deficit
            else:
                calorie_target = int(tdee)

            print(f"   BMR: {bmr:.0f} kcal | TDEE: {tdee:.0f} kcal | Target: {calorie_target} kcal")

        except Exception as e:
            print(f"   ⚠️ BMR calculation failed ({e}), using defaults.")

    # ── Fall back to defaults if profile data is incomplete ──────────────────
    if calorie_target is None:
        calorie_target = DEFAULT_CALORIES[goal_type]
        print(f"   ℹ️ Using default calorie target ({calorie_target} kcal) — profile data incomplete.")

    macro_split = DEFAULT_MACROS[goal_type]

    print(f"✅ Goal: {goal_type} | Calories: {calorie_target} | Macros: {macro_split}")

    # ── Return ONLY the keys this agent sets ─────────────────────────────────
    return {
        "calorie_target":   calorie_target,
        "macro_split":      macro_split,
        "goal_interpreted": True,
    }