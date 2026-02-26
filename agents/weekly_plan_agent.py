"""
agents/weekly_plan_agent.py

Generates a full 7-day meal plan.

Logic:
1. Calculate per-meal calorie distribution based on meal frequency
2. Generate each day's meals via LLM with structured output
3. Enforce variety: no dish repeated within any rolling 3-day window
4. Compute DayPlan totals and WeeklyNutritionSummary
5. Returns MealPlan in state
"""

from __future__ import annotations

from state import WeeklyPlanState
from schemas.nutrition_schemas import (
    MealPlan, DayPlan, MealSlot, WeeklyNutritionSummary,
    RecipeOutput, MealSlotType, DayOfWeek,
)
from memory.recipe_context_store import retrieve_context
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")

# Structured output for a single meal slot
llm_meal = model.with_structured_output(RecipeOutput)

DAYS: list[DayOfWeek] = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]

# ── Calorie distribution per slot ─────────────────────────────────────────────
SLOT_DISTRIBUTION = {
    "breakfast": 0.25,
    "lunch":     0.35,
    "dinner":    0.30,
    "snack":     0.10,
}

MEAL_SLOTS: list[MealSlotType] = ["breakfast", "lunch", "dinner", "snack"]

# ── Per-meal prompt ────────────────────────────────────────────────────────────
MEAL_PROMPT = ChatPromptTemplate.from_template("""
You are a world-class nutritionist and chef creating a weekly meal plan.

Generate ONE {meal_slot} recipe for {day_of_week}.

━━━━━━━━━━━━━━━━━━━
👤 PROFILE
━━━━━━━━━━━━━━━━━━━
- Fitness Goal: {fitness_goal}
- Calorie Target for this meal: {meal_calorie_target} kcal
- Full-day macro split — Protein {protein_pct}% | Carbs {carbs_pct}% | Fat {fat_pct}%
- Cuisine: {cuisine} | Spice: {spice_level}
- Allergies: {allergies}
- Medical conditions: {medical_conditions}
- Age group: {age_group}

━━━━━━━━━━━━━━━━━━━
🚫 VARIETY RULE (CRITICAL)
━━━━━━━━━━━━━━━━━━━
These dishes have already been used in the last 3 days — DO NOT repeat them:
{recent_dishes}

━━━━━━━━━━━━━━━━━━━
📚 REFERENCE EXAMPLES
━━━━━━━━━━━━━━━━━━━
{recipe_context}

━━━━━━━━━━━━━━━━━━━
🎯 REQUIREMENTS
━━━━━━━━━━━━━━━━━━━
- Calories within ±15% of {meal_calorie_target} kcal
- Appropriate for {meal_slot} (light for breakfast/snack, substantial for lunch/dinner)
- Must be a DIFFERENT dish from the ones listed above
- Include fiber (aim for 3-5g per meal)
- Set meal_type = "{meal_slot}"

Return a complete recipe with ingredients, steps, and full nutrition.
""")


def _format_context(contexts) -> str:
    if not contexts:
        return "Use your best culinary judgment."
    lines = []
    for ctx in contexts:
        lines.append(f"- {ctx.dish_name} ({ctx.cuisine}) ~{ctx.approx_calories} kcal | {ctx.notes}")
    return "\n".join(lines)


def _compute_day_totals(meals: list[MealSlot]) -> tuple[int, float, float, float, float]:
    """Returns (calories, protein_g, carbs_g, fat_g, fiber_g)."""
    cals = sum(m.recipe.nutrition.calories for m in meals)
    prot = sum(m.recipe.nutrition.protein_g for m in meals)
    carb = sum(m.recipe.nutrition.carbs_g   for m in meals)
    fat  = sum(m.recipe.nutrition.fat_g     for m in meals)
    fib  = sum(m.recipe.nutrition.fiber_g or 0 for m in meals)
    return cals, prot, carb, fat, fib


def _compute_weekly_summary(
    day_plans: list[DayPlan],
    calorie_target: int,
) -> WeeklyNutritionSummary:
    n = len(day_plans)
    total_cal  = sum(d.total_calories  for d in day_plans)
    total_prot = sum(d.total_protein_g for d in day_plans)
    total_carb = sum(d.total_carbs_g   for d in day_plans)
    total_fat  = sum(d.total_fat_g     for d in day_plans)
    total_fib  = sum(d.total_fiber_g   for d in day_plans)

    hit_days = sum(
        1 for d in day_plans
        if abs(d.total_calories - calorie_target) / calorie_target <= 0.10
    )

    return WeeklyNutritionSummary(
        avg_daily_calories  = round(total_cal  / n, 1),
        avg_daily_protein_g = round(total_prot / n, 1),
        avg_daily_carbs_g   = round(total_carb / n, 1),
        avg_daily_fat_g     = round(total_fat  / n, 1),
        avg_daily_fiber_g   = round(total_fib  / n, 1),
        total_weekly_calories    = total_cal,
        calorie_target_hit_days  = hit_days,
        notes = f"{hit_days}/7 days hit calorie target (±10%).",
    )


def weekly_plan_agent_node(state: WeeklyPlanState) -> dict:
    print("\n📅 Generating 7-day meal plan...")

    macro       = state.macro_split
    cuisine     = state.preferences.get("cuisine", "any")
    goal_type   = state.goal_type or "maintenance"
    conditions  = state.medical_conditions or []
    age_group   = state.age_profile.age_group if state.age_profile else "adult"
    cal_target  = state.calorie_target or 2200
    conditions_str = ", ".join(c.condition for c in conditions) if conditions else "none"

    day_plans: list[DayPlan] = []

    # Sliding window of recent dish names for variety enforcement
    recent_dishes: list[str] = []

    contexts = retrieve_context(goal_type=goal_type, cuisine=cuisine, n=3)
    context_text = _format_context(contexts)

    for day in DAYS:
        print(f"   Generating {day}...")
        day_meals: list[MealSlot] = []

        for slot in MEAL_SLOTS:
            slot_cal = int(cal_target * SLOT_DISTRIBUTION[slot])
            recent_str = ", ".join(recent_dishes[-9:]) if recent_dishes else "none yet"

            messages = MEAL_PROMPT.format_messages(
                meal_slot=slot,
                day_of_week=day,
                fitness_goal=state.fitness_goal or "maintenance",
                meal_calorie_target=slot_cal,
                protein_pct=macro.protein,
                carbs_pct=macro.carbs,
                fat_pct=macro.fat,
                cuisine=cuisine,
                spice_level=state.preferences.get("spice_level", "medium"),
                allergies=", ".join(state.allergies) if state.allergies else "none",
                medical_conditions=conditions_str,
                age_group=age_group,
                recent_dishes=recent_str,
                recipe_context=context_text,
            )

            recipe: RecipeOutput = llm_meal.invoke(messages)

            day_meals.append(MealSlot(
                slot=slot,
                recipe=recipe,
                target_calories=slot_cal,
            ))

            # Track for variety enforcement (rolling window of 9 = 3 days × 3 meals)
            recent_dishes.append(recipe.dish_name)
            if len(recent_dishes) > 9:
                recent_dishes.pop(0)

        cals, prot, carb, fat, fib = _compute_day_totals(day_meals)

        day_plans.append(DayPlan(
            day=day,
            meals=day_meals,
            total_calories=cals,
            total_protein_g=prot,
            total_carbs_g=carb,
            total_fat_g=fat,
            total_fiber_g=fib,
        ))
        print(f"      ✅ {day}: {cals} kcal | P:{prot:.0f}g C:{carb:.0f}g F:{fat:.0f}g")

    summary  = _compute_weekly_summary(day_plans, cal_target)
    meal_plan = MealPlan(days=day_plans, weekly_summary=summary)

    print(f"\n✅ Meal plan complete.")
    print(f"   Avg daily: {summary.avg_daily_calories} kcal | "
          f"P:{summary.avg_daily_protein_g}g C:{summary.avg_daily_carbs_g}g F:{summary.avg_daily_fat_g}g")
    print(f"   {summary.notes}")

    return {
        "meal_plan":      meal_plan,
        "plan_generated": True,
    }