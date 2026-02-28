"""
memory/recipe_context_store.py — Phase 4

Upgraded from static keyword matching to ChromaDB semantic search.

Retrieval flow:
  1. Try ChromaDB vector search (semantic similarity)
  2. If ChromaDB unavailable or returns 0 results, fall back to
     keyword matching against RECIPE_BANK (Phase 3 behaviour)

This means the system works with or without ChromaDB installed.
"""

from __future__ import annotations

from schemas.nutrition_schemas import RecipeContext

# ── Static recipe bank (unchanged from Phase 3) ───────────────────────────────
# This is the ground truth — ChromaDB is seeded FROM this bank.
RECIPE_BANK: list[RecipeContext] = [
    RecipeContext(dish_name="Chicken Karahi", cuisine="pakistani", goal_fit="muscle_gain",
        key_proteins=["chicken"], approx_calories=520,
        notes="High protein, medium fat from oil. Serve with 1 roti for carbs."),
    RecipeContext(dish_name="Daal Mash with Brown Rice", cuisine="pakistani", goal_fit="maintenance",
        key_proteins=["urad lentils"], approx_calories=420,
        notes="Plant-based protein, complex carbs, low fat. Good fiber content."),
    RecipeContext(dish_name="Grilled Tandoori Chicken with Raita", cuisine="pakistani", goal_fit="fat_loss",
        key_proteins=["chicken breast"], approx_calories=350,
        notes="Lean protein, minimal oil, yogurt raita adds probiotics."),
    RecipeContext(dish_name="Keema Methi with Chapati", cuisine="pakistani", goal_fit="muscle_gain",
        key_proteins=["ground beef", "fenugreek leaves"], approx_calories=580,
        notes="Dense protein + iron from beef. Fenugreek aids digestion."),
    RecipeContext(dish_name="Paneer Tikka", cuisine="indian", goal_fit="muscle_gain",
        key_proteins=["paneer"], approx_calories=450,
        notes="High protein vegetarian. Grill, don't fry."),
    RecipeContext(dish_name="Dal Tadka with Brown Rice", cuisine="indian", goal_fit="maintenance",
        key_proteins=["toor dal"], approx_calories=400,
        notes="Balanced plant protein + complex carbs."),
    RecipeContext(dish_name="Chicken Tikka Salad", cuisine="indian", goal_fit="fat_loss",
        key_proteins=["chicken breast"], approx_calories=310,
        notes="Low calorie, high protein. Skip the rice."),
    RecipeContext(dish_name="Grilled Salmon Pasta", cuisine="italian", goal_fit="muscle_gain",
        key_proteins=["salmon"], approx_calories=620,
        notes="Omega-3 rich protein + complex carbs. Use whole wheat pasta."),
    RecipeContext(dish_name="Chicken with Zucchini and Tomato", cuisine="italian", goal_fit="fat_loss",
        key_proteins=["chicken breast"], approx_calories=330,
        notes="Low carb, high protein. No pasta."),
    RecipeContext(dish_name="Stir-Fried Tofu with Brown Rice", cuisine="chinese", goal_fit="maintenance",
        key_proteins=["tofu"], approx_calories=380,
        notes="Plant-based, balanced macros."),
    RecipeContext(dish_name="Egg White Omelette with Spinach", cuisine="any", goal_fit="fat_loss",
        key_proteins=["egg whites"], approx_calories=250,
        notes="Ultra-lean breakfast. High protein, very low fat."),
    RecipeContext(dish_name="Oats with Banana and Peanut Butter", cuisine="any", goal_fit="muscle_gain",
        key_proteins=["oats", "peanut butter"], approx_calories=520,
        notes="Pre-workout meal. Slow carbs + protein + healthy fat."),
    RecipeContext(dish_name="Grilled Chicken with Sweet Potato", cuisine="any", goal_fit="muscle_gain",
        key_proteins=["chicken breast"], approx_calories=550,
        notes="Classic clean bulk plate."),
]


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve_context(goal_type: str, cuisine: str, n: int = 2) -> list[RecipeContext]:
    """
    Retrieve n most relevant recipe examples.

    Tries ChromaDB semantic search first.
    Falls back to keyword matching if ChromaDB is unavailable.
    """
    # ── Try vector search ─────────────────────────────────────────────────────
    try:
        from vector_store.chroma_store import chroma_store
        if chroma_store.available:
            query = f"healthy {goal_type.replace('_', ' ')} {cuisine} meal"
            results = chroma_store.search_recipes(
                query=query, goal_type=goal_type, cuisine=cuisine, n=n,
            )
            if results:
                return [
                    RecipeContext(
                        dish_name=r["dish_name"],
                        cuisine=r["cuisine"],
                        goal_fit=r["goal_fit"],
                        key_proteins=r["key_proteins"],
                        approx_calories=r["approx_calories"],
                        notes=r["notes"],
                    )
                    for r in results
                ]
    except Exception:
        pass   # fall through to keyword matching

    # ── Keyword fallback (Phase 3 behaviour) ──────────────────────────────────
    cuisine_lower = (cuisine or "any").lower()

    exact = [
        r for r in RECIPE_BANK
        if r.goal_fit == goal_type
        and (r.cuisine == cuisine_lower or cuisine_lower in r.cuisine)
    ]
    if len(exact) >= n:
        return exact[:n]

    fallback = [r for r in RECIPE_BANK if r.goal_fit == goal_type and r.cuisine == "any"]
    combined = exact + fallback
    return combined[:n] if len(combined) >= n else combined