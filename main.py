"""
main.py — Phase 3

Unified entry point with 4 modes:

  python main.py                     → single meal (default)
  python main.py --mode weekly       → 7-day meal plan + grocery + prep
  python main.py --mode image        → food photo → nutrition log
  python main.py --mode progress     → weekly progress report

The user profile is collected once and reused across all modes.
"""

import argparse
import sys

from state import NutritionState, WeeklyPlanState


# ═══════════════════════════════════════════════════════════════
# Display helpers
# ═══════════════════════════════════════════════════════════════

def print_recipe(recipe) -> None:
    if not recipe:
        print("No recipe available.")
        return
    print(f"\n🍽️  {recipe.dish_name}")
    if recipe.cuisine:        print(f"   Cuisine:   {recipe.cuisine}")
    if recipe.meal_type:      print(f"   Meal type: {recipe.meal_type}")
    if recipe.prep_time_minutes: print(f"   Prep time: {recipe.prep_time_minutes} min")
    print("\n🧾 Ingredients:")
    for ing in recipe.ingredients:
        print(f"   - {ing.quantity}  {ing.name}")
    print("\n👨‍🍳 Steps:")
    for i, step in enumerate(recipe.steps, 1):
        print(f"   {i}. {step}")
    n = recipe.nutrition
    print("\n📊 Nutrition:")
    print(f"   Calories: {n.calories} kcal  |  P:{n.protein_g}g  C:{n.carbs_g}g  F:{n.fat_g}g", end="")
    if n.fiber_g:   print(f"  |  Fiber:{n.fiber_g}g", end="")
    if n.sodium_mg: print(f"  |  Na:{n.sodium_mg}mg", end="")
    print()


def print_meal_plan(meal_plan) -> None:
    if not meal_plan:
        print("No meal plan available.")
        return
    print("\n📅 7-DAY MEAL PLAN")
    print("=" * 70)
    for day in meal_plan.days:
        print(f"\n{'─'*70}")
        print(f"  {day.day.upper()}  —  {day.total_calories} kcal total")
        print(f"  P:{day.total_protein_g:.0f}g  C:{day.total_carbs_g:.0f}g  F:{day.total_fat_g:.0f}g  Fiber:{day.total_fiber_g:.0f}g")
        for slot in day.meals:
            n = slot.recipe.nutrition
            print(f"  [{slot.slot:10}] {slot.recipe.dish_name:40} {n.calories:>4} kcal")

    s = meal_plan.weekly_summary
    print(f"\n{'═'*70}")
    print("📊 WEEKLY SUMMARY")
    print(f"   Avg/day: {s.avg_daily_calories} kcal | P:{s.avg_daily_protein_g}g C:{s.avg_daily_carbs_g}g F:{s.avg_daily_fat_g}g")
    print(f"   Total weekly: {s.total_weekly_calories:,} kcal")
    print(f"   {s.notes}")


def print_grocery_list(grocery) -> None:
    if not grocery:
        print("No grocery list available.")
        return
    print("\n🛒 GROCERY LIST")
    print("=" * 60)
    by_cat = grocery.by_category()
    for category, items in sorted(by_cat.items()):
        print(f"\n  {category.upper()}")
        for item in items:
            cost = f"  ~PKR {item.estimated_cost_pkr:.0f}" if item.estimated_cost_pkr else ""
            print(f"    • {item.total_quantity:15} {item.name}{cost}")
            if item.bulk_buy_tip:
                print(f"      💡 {item.bulk_buy_tip}")

    if grocery.estimated_total_cost_pkr:
        print(f"\n  💰 Estimated total: PKR {grocery.estimated_total_cost_pkr:,.0f}")
    if grocery.shopping_notes:
        print(f"\n  📝 {grocery.shopping_notes}")


def print_prep_schedule(schedule) -> None:
    if not schedule:
        print("No prep schedule available.")
        return
    print("\n🥘 MEAL PREP SCHEDULE")
    print("=" * 60)
    print(f"   Total prep time: {schedule.total_prep_time_min} min across {schedule.prep_days}")
    if schedule.efficiency_notes:
        print(f"   {schedule.efficiency_notes}")
    for task in schedule.tasks:
        print(f"\n  [{task.prep_day}] {task.task}")
        print(f"         ⏱️  {task.duration_minutes} min")
        print(f"         📦 {task.storage_instruction}")
        if task.reheating_tip:
            print(f"         🔥 {task.reheating_tip}")
        print(f"         Covers: {', '.join(task.covers_meals)}")


def print_progress_report(report) -> None:
    if not report:
        print("No progress report available.")
        return
    print("\n📈 WEEKLY PROGRESS REPORT")
    print("=" * 60)
    print(f"   Period: {report.week_start} → {report.week_end}")
    print(f"   Avg adherence: {report.avg_adherence_pct:.1f}%")
    print(f"   Best day: {report.best_day}  |  Worst day: {report.worst_day}")
    print(f"\n   Goal progress: {report.goal_progress}")
    print("\n   🔍 Patterns identified:")
    for p in report.patterns_identified:
        print(f"      • {p}")
    print("\n   💡 Recommendations:")
    for r in report.recommendations:
        print(f"      • {r}")
    if report.motivational_note:
        print(f"\n   ✨ {report.motivational_note}")


# ═══════════════════════════════════════════════════════════════
# Profile collection helper (shared across modes)
# ═══════════════════════════════════════════════════════════════

def collect_profile() -> NutritionState:
    """Run profile_agent to get user profile, then health_agent for targets."""
    from agents.profile_agent import profile_agent_node
    from agents.health_agent  import health_goal_agent_node

    state = profile_agent_node(NutritionState())
    updates = health_goal_agent_node(state)
    return state.model_copy(update=updates)


# ═══════════════════════════════════════════════════════════════
# Mode: Single Meal
# ═══════════════════════════════════════════════════════════════

def run_single_meal() -> None:
    from graph_builder import graph

    print("🍽️  SINGLE MEAL MODE\n")
    raw   = graph.invoke(NutritionState())
    state = NutritionState(**raw)

    if state.age_profile:
        print(f"\n[Age group: {state.age_profile.age_group} — {state.age_profile.notes}]")

    print("\n" + "="*60)
    print("FINAL PERSONALIZED RECIPE")
    print("="*60)
    print_recipe(state.final_recipe)

    print("\n" + "="*60)
    print("NUTRITION VALIDATION")
    print("="*60)
    if state.validation_notes:
        print(state.validation_notes)

    if state.substitutions_made and state.substitution_output:
        print("\n" + "="*60)
        print("SUBSTITUTIONS MADE")
        print("="*60)
        for sub in state.substitution_output.substitutions:
            print(f"  {sub.original_ingredient} → {sub.substitute_ingredient}")
            print(f"  Reason: {sub.reason}\n")

    print("\n" + "="*60)
    print("WHY THIS RECIPE?")
    print("="*60)
    print(state.recipe_explanation or "No explanation generated.")

    print(f"\nRating: {'⭐' * (state.feedback_rating or 0)}")
    print(f"Comment: {state.feedback_comment or 'None'}")

    if state.learned_preferences:
        lp = state.learned_preferences
        print("\n📚 Learned Preferences:")
        if lp.liked_ingredients:    print(f"  Likes:    {', '.join(lp.liked_ingredients)}")
        if lp.disliked_ingredients: print(f"  Dislikes: {', '.join(lp.disliked_ingredients)}")
        if lp.goal_refinement:      print(f"  Goal:     {lp.goal_refinement}")


# ═══════════════════════════════════════════════════════════════
# Mode: Weekly Plan
# ═══════════════════════════════════════════════════════════════

def run_weekly_plan() -> None:
    from weekly_graph_builder import weekly_graph

    print("📅  WEEKLY MEAL PLAN MODE\n")
    profile = collect_profile()

    # Bootstrap WeeklyPlanState from profile
    weekly_state = WeeklyPlanState(
        name=profile.name,
        age=profile.age,
        gender=profile.gender,
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        activity_level=profile.activity_level,
        allergies=profile.allergies,
        preferences=profile.preferences,
        fitness_goal=profile.fitness_goal,
        medical_conditions=profile.medical_conditions,
        calorie_target=profile.calorie_target,
        macro_split=profile.macro_split,
        goal_type=profile.goal_type,
        age_profile=profile.age_profile,
        learned_preferences=profile.learned_preferences,
    )

    raw   = weekly_graph.invoke(weekly_state)
    state = WeeklyPlanState(**raw)

    print_meal_plan(state.meal_plan)
    print_grocery_list(state.grocery_list)
    print_prep_schedule(state.prep_schedule)


# ═══════════════════════════════════════════════════════════════
# Mode: Image Scan
# ═══════════════════════════════════════════════════════════════

def run_image_scan() -> None:
    from agents.image_agent import image_agent_node, confirm_and_log_image

    print("📷  FOOD IMAGE SCAN MODE\n")
    image_path = input("Enter path to food image (JPG/PNG): ").strip()

    profile = collect_profile()
    state   = profile.model_copy(update={"image_path": image_path})

    updates = image_agent_node(state)
    state   = state.model_copy(update=updates)

    if state.image_analysis:
        print("\n🔍 Image Analysis:")
        for item in state.image_analysis.identified_items:
            print(f"  [{item.confidence}] {item.name} — {item.estimated_amount}")

    confirm_and_log_image(state)


# ═══════════════════════════════════════════════════════════════
# Mode: Progress Report
# ═══════════════════════════════════════════════════════════════

def run_progress() -> None:
    from agents.progress_agent import progress_agent_node

    print("📈  WEEKLY PROGRESS REPORT MODE\n")
    profile = collect_profile()
    updates = progress_agent_node(profile)
    state   = profile.model_copy(update=updates)
    print_progress_report(state.progress_report)


# ═══════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nutrition AI Chef")
    parser.add_argument(
        "--mode",
        choices=["meal", "weekly", "image", "progress"],
        default="meal",
        help="Run mode (default: meal)",
    )
    args = parser.parse_args()

    mode_map = {
        "meal":     run_single_meal,
        "weekly":   run_weekly_plan,
        "image":    run_image_scan,
        "progress": run_progress,
    }

    mode_map[args.mode]()