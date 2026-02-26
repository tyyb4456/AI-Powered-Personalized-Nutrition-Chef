"""
main.py — Phase 2
"""

from graph_builder import graph
from state import NutritionState


def print_recipe(recipe) -> None:
    if recipe is None:
        print("No recipe available.")
        return

    print(f"\n🍽️  {recipe.dish_name}")
    if recipe.cuisine:
        print(f"   Cuisine:   {recipe.cuisine}")
    if recipe.meal_type:
        print(f"   Meal type: {recipe.meal_type}")
    if recipe.prep_time_minutes:
        print(f"   Prep time: {recipe.prep_time_minutes} min")

    print("\n🧾 Ingredients:")
    for ing in recipe.ingredients:
        print(f"   - {ing.quantity}  {ing.name}")

    print("\n👨‍🍳 Steps:")
    for i, step in enumerate(recipe.steps, 1):
        print(f"   {i}. {step}")

    print("\n📊 Nutrition:")
    n = recipe.nutrition
    print(f"   Calories:  {n.calories} kcal")
    print(f"   Protein:   {n.protein_g}g")
    print(f"   Carbs:     {n.carbs_g}g")
    print(f"   Fat:       {n.fat_g}g")
    if n.fiber_g is not None:
        print(f"   Fiber:     {n.fiber_g}g")
    if n.sodium_mg is not None:
        print(f"   Sodium:    {n.sodium_mg}mg")


if __name__ == "__main__":
    print("🍽️  Starting Personalized Nutrition Chef (Phase 2)...\n")

    raw   = graph.invoke(NutritionState())
    state = NutritionState(**raw)

    # ── Age Profile ───────────────────────────────────────────────────────────
    if state.age_profile:
        print("\n" + "="*60)
        print("AGE PROFILE")
        print("="*60)
        ap = state.age_profile
        print(f"Group: {ap.age_group}")
        print(f"Notes: {ap.notes}")

    # ── Final Recipe ──────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("FINAL PERSONALIZED RECIPE")
    print("="*60)
    print_recipe(state.final_recipe)

    # ── Validation ────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("NUTRITION VALIDATION")
    print("="*60)
    if state.validation_notes:
        print(state.validation_notes)

    # ── Substitutions ─────────────────────────────────────────────────────────
    if state.substitutions_made and state.substitution_output:
        print("\n" + "="*60)
        print("SUBSTITUTIONS MADE")
        print("="*60)
        for sub in state.substitution_output.substitutions:
            print(f"  {sub.original_ingredient} → {sub.substitute_ingredient}")
            print(f"  Reason: {sub.reason}\n")

    # ── Explanation ───────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("WHY THIS RECIPE?")
    print("="*60)
    print(state.recipe_explanation or "No explanation generated.")

    # ── Feedback ──────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("YOUR FEEDBACK")
    print("="*60)
    print(f"Rating:  {'⭐' * (state.feedback_rating or 0)}")
    print(f"Comment: {state.feedback_comment or 'None'}")

    # ── Learned Preferences ───────────────────────────────────────────────────
    if state.learned_preferences:
        print("\n" + "="*60)
        print("LEARNED PREFERENCES (saved for next session)")
        print("="*60)
        lp = state.learned_preferences
        if lp.liked_ingredients:
            print(f"  ✅ Likes:    {', '.join(lp.liked_ingredients)}")
        if lp.disliked_ingredients:
            print(f"  ❌ Dislikes: {', '.join(lp.disliked_ingredients)}")
        if lp.goal_refinement:
            print(f"  🎯 Goal update: {lp.goal_refinement}")
        if lp.session_insights:
            print("  💡 Insights:")
            for note in lp.session_insights:
                print(f"     - {note}")