"""
main.py — Phase 5

Phase 5 change:
- ChromaDB replaced with LangChain RAG (FAISS) for vector search
- startup() seeds LangChain FAISS store instead of ChromaDB
- All other run modes unchanged

Usage:
  python main.py                     → single meal
  python main.py --mode weekly       → 7-day plan
  python main.py --mode image        → photo scan + log
  python main.py --mode progress     → weekly report
"""

import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from state import NutritionState, WeeklyPlanState


# ═══════════════════════════════════════════════════════════════
# Startup: initialise all persistence layers
# ═══════════════════════════════════════════════════════════════

def startup() -> None:
    """
    Called once at process start.
    Safe to run in any environment — failures are warnings, not crashes.
    """
    # ── 1. PostgreSQL tables ──────────────────────────────────────────────────
    try:
        from db.database import create_tables
        create_tables()
    except Exception as e:
        logger.warning("DB init failed (%s). Running without persistence.", e)

    # ── 2. LangChain FAISS — seed recipe bank if not yet indexed ─────────────
    try:
        from vector_store.langchain_store import langchain_store
        if langchain_store.available:
            count = langchain_store.seed_from_recipe_bank()
            if count:
                print(f"   🔍 LangChain FAISS seeded with {count} recipe examples.")
        else:
            print("   ⚠️ LangChain FAISS unavailable — falling back to keyword matching.")
    except Exception as e:
        logger.warning("LangChain FAISS seed failed (%s).", e)

    # ── 3. Redis health check ─────────────────────────────────────────────────
    try:
        from cache.redis_client import redis_client
        if redis_client.available:
            print("   ⚡ Redis cache connected.")
        else:
            print("   ⚠️ Redis unavailable — caching disabled.")
    except Exception as e:
        logger.warning("Redis check failed (%s).", e)


# ═══════════════════════════════════════════════════════════════
# Display helpers (unchanged from Phase 3)
# ═══════════════════════════════════════════════════════════════

def print_recipe(recipe) -> None:
    if not recipe: print("No recipe available."); return
    print(f"\n🍽️  {recipe.dish_name}")
    if recipe.cuisine:           print(f"   Cuisine:   {recipe.cuisine}")
    if recipe.meal_type:         print(f"   Meal type: {recipe.meal_type}")
    if recipe.prep_time_minutes: print(f"   Prep time: {recipe.prep_time_minutes} min")
    print("\n🧾 Ingredients:")
    for ing in recipe.ingredients:
        print(f"   - {ing.quantity}  {ing.name}")
    print("\n👨‍🍳 Steps:")
    for i, step in enumerate(recipe.steps, 1):
        print(f"   {i}. {step}")
    n = recipe.nutrition
    print(f"\n📊 Nutrition: {n.calories} kcal | P:{n.protein_g}g C:{n.carbs_g}g F:{n.fat_g}g", end="")
    if n.fiber_g:   print(f" | Fiber:{n.fiber_g}g", end="")
    if n.sodium_mg: print(f" | Na:{n.sodium_mg}mg", end="")
    print()


def print_meal_plan(meal_plan) -> None:
    if not meal_plan: return
    print("\n📅 7-DAY MEAL PLAN")
    print("=" * 70)
    for day in meal_plan.days:
        print(f"\n{'─'*70}")
        print(f"  {day.day.upper()}  —  {day.total_calories} kcal | P:{day.total_protein_g:.0f}g C:{day.total_carbs_g:.0f}g F:{day.total_fat_g:.0f}g")
        for slot in day.meals:
            print(f"  [{slot.slot:10}] {slot.recipe.dish_name:40} {slot.recipe.nutrition.calories:>4} kcal")
    s = meal_plan.weekly_summary
    print(f"\n{'═'*70}")
    print(f"📊 Avg/day: {s.avg_daily_calories} kcal | {s.notes}")


def print_grocery_list(grocery) -> None:
    if not grocery: return
    print("\n🛒 GROCERY LIST")
    print("=" * 60)
    for category, items in sorted(grocery.by_category().items()):
        print(f"\n  {category.upper()}")
        for item in items:
            cost = f"  ~PKR {item.estimated_cost_pkr:.0f}" if item.estimated_cost_pkr else ""
            print(f"    • {item.total_quantity:15} {item.name}{cost}")
            if item.bulk_buy_tip: print(f"      💡 {item.bulk_buy_tip}")
    if grocery.estimated_total_cost_pkr:
        print(f"\n  💰 Estimated total: PKR {grocery.estimated_total_cost_pkr:,.0f}")


def print_prep_schedule(schedule) -> None:
    if not schedule: return
    print("\n🥘 MEAL PREP SCHEDULE")
    print("=" * 60)
    print(f"   Total: {schedule.total_prep_time_min} min | Days: {schedule.prep_days}")
    for task in schedule.tasks:
        print(f"\n  [{task.prep_day}] {task.task} ({task.duration_minutes} min)")
        print(f"         📦 {task.storage_instruction}")
        if task.reheating_tip: print(f"         🔥 {task.reheating_tip}")
        print(f"         Covers: {', '.join(task.covers_meals)}")


def print_progress_report(report) -> None:
    if not report: return
    print("\n📈 WEEKLY PROGRESS REPORT")
    print("=" * 60)
    print(f"   {report.week_start} → {report.week_end}")
    print(f"   Avg adherence: {report.avg_adherence_pct:.1f}% | Best: {report.best_day} | Worst: {report.worst_day}")
    print(f"\n   {report.goal_progress}")
    for p in report.patterns_identified: print(f"   • {p}")
    print("\n   Recommendations:")
    for r in report.recommendations:     print(f"   • {r}")
    if report.motivational_note:         print(f"\n   ✨ {report.motivational_note}")


# ═══════════════════════════════════════════════════════════════
# Profile collection with session resume
# ═══════════════════════════════════════════════════════════════

def collect_profile() -> NutritionState:
    """Run profile + health agents. Offers session resume from Redis."""
    from agents.profile_agent import profile_agent_node
    from agents.health_agent  import health_goal_agent_node

    # ── Check Redis for an active session before collecting profile ───────────
    name_guess = input("Enter your name (for session lookup): ").strip()
    if name_guess:
        try:
            from cache.redis_client import redis_client
            cached_state = redis_client.load_session(name_guess)
            if cached_state:
                resume = input(f"   ⚡ Active session found for '{name_guess}'. Resume? (y/n): ").strip().lower()
                if resume == "y":
                    print("   ✅ Session restored from cache.")
                    return NutritionState(**cached_state)
        except Exception:
            pass

    # ── Full profile collection ───────────────────────────────────────────────
    # We already asked for the name above — inject it into stdin isn't clean,
    # so we rely on profile_agent_node asking again. In a real app this would
    # be passed as a parameter. For CLI it's an acceptable two-step.
    state   = profile_agent_node(NutritionState())
    updates = health_goal_agent_node(state)
    state   = state.model_copy(update=updates)

    # ── Cache the session ─────────────────────────────────────────────────────
    try:
        from cache.redis_client import redis_client
        user_key = state.customer_id or state.name or "anonymous"
        redis_client.save_session(user_key, state.model_dump())
    except Exception:
        pass

    return state


# ═══════════════════════════════════════════════════════════════
# Run modes
# ═══════════════════════════════════════════════════════════════

def run_single_meal() -> None:
    import uuid
    from graph_builder import invoke_for_user, resume_for_user, get_interrupt_prompt
    print("🍽️  SINGLE MEAL MODE\n")

    # Fresh UUID per run so state never bleeds between sessions
    thread_id = str(uuid.uuid4())

    # ── Step 1: start the graph ───────────────────────────────────────────────
    # invoke_for_user runs until END or until an interrupt() is hit.
    # When feedback_agent calls interrupt(), LangGraph raises GraphInterrupt
    # and graph.invoke() returns the CURRENT state snapshot (not the final one).
    raw = invoke_for_user(thread_id, NutritionState())

    # ── Step 2: handle interrupts (feedback_agent has two: rating + comment) ──
    # After each interrupt, get_interrupt_prompt() tells us what the graph
    # is waiting for, we ask the user, then resume_for_user() continues.
    while True:
        prompt = get_interrupt_prompt(thread_id)
        if prompt is None:
            break   # graph reached END — no more interrupts
        user_answer = input(f"{prompt} ").strip()
        raw = resume_for_user(thread_id, user_answer)

    # ── Step 3: render final output ───────────────────────────────────────────
    state = NutritionState(**raw)

    if state.age_profile:
        print(f"\n[Age group: {state.age_profile.age_group}]")

    print("\n" + "="*60 + "\nFINAL RECIPE\n" + "="*60)
    print_recipe(state.final_recipe)

    print("\n" + "="*60 + "\nVALIDATION\n" + "="*60)
    if state.validation_notes: print(state.validation_notes)

    if state.substitutions_made and state.substitution_output:
        print("\n" + "="*60 + "\nSUBSTITUTIONS\n" + "="*60)
        for sub in state.substitution_output.substitutions:
            print(f"  {sub.original_ingredient} → {sub.substitute_ingredient}: {sub.reason}")

    print("\n" + "="*60 + "\nWHY THIS RECIPE?\n" + "="*60)
    print(state.recipe_explanation or "No explanation generated.")

    print(f"\nRating: {'⭐' * (state.feedback_rating or 0)}")
    if state.learned_preferences:
        lp = state.learned_preferences
        if lp.liked_ingredients:    print(f"Learned likes:    {', '.join(lp.liked_ingredients)}")
        if lp.disliked_ingredients: print(f"Learned dislikes: {', '.join(lp.disliked_ingredients)}")


def run_weekly_plan() -> None:
    from weekly_graph_builder import weekly_graph
    print("📅  WEEKLY MEAL PLAN MODE\n")
    profile = collect_profile()

    weekly_state = WeeklyPlanState(
        name=profile.name, age=profile.age, gender=profile.gender,
        weight_kg=profile.weight_kg, height_cm=profile.height_cm,
        activity_level=profile.activity_level, allergies=profile.allergies,
        preferences=profile.preferences, fitness_goal=profile.fitness_goal,
        medical_conditions=profile.medical_conditions,
        calorie_target=profile.calorie_target, macro_split=profile.macro_split,
        goal_type=profile.goal_type, age_profile=profile.age_profile,
        learned_preferences=profile.learned_preferences,
    )

    raw   = weekly_graph.invoke(weekly_state, config={"configurable": {"thread_id": str(__import__("uuid").uuid4())}})
    state = WeeklyPlanState(**raw)

    print_meal_plan(state.meal_plan)
    print_grocery_list(state.grocery_list)
    print_prep_schedule(state.prep_schedule)


def run_image_scan() -> None:
    from agents.image_agent import image_agent_node, confirm_and_log_image
    print("📷  FOOD IMAGE SCAN MODE\n")
    image_path = input("Enter path to food image (JPG/PNG): ").strip()
    profile    = collect_profile()
    state      = profile.model_copy(update={"image_path": image_path})
    updates    = image_agent_node(state)
    state      = state.model_copy(update=updates)
    if state.image_analysis:
        for item in state.image_analysis.identified_items:
            print(f"  [{item.confidence}] {item.name} — {item.estimated_amount}")
    confirm_and_log_image(state)


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
    parser = argparse.ArgumentParser(description="Nutrition AI Chef — Phase 4")
    parser.add_argument(
        "--mode", choices=["meal", "weekly", "image", "progress"],
        default="meal", help="Run mode (default: meal)",
    )
    args = parser.parse_args()

    print("🚀 Nutrition AI Chef — Phase 4\n")
    startup()
    print()

    {"meal": run_single_meal, "weekly": run_weekly_plan,
     "image": run_image_scan, "progress": run_progress}[args.mode]()