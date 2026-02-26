"""
memory/recipe_context_store.py

Phase 2: RAG-style context injection.

Instead of letting the LLM hallucinate recipes from scratch,
we inject 2–3 relevant example recipes as context into the prompt.

This is a static in-memory store for now.
Phase 3 will replace this with a proper vector DB (ChromaDB / Pinecone)
seeded with a real recipe dataset.

How it works:
1. User profile has cuisine preference + goal_type
2. retrieve_context() finds matching examples
3. Examples are injected into the recipe prompt as few-shot context
4. LLM adapts them to exact user macros — much more reliable than blank generation
"""

from schemas.nutrition_schemas import RecipeContext


# ─────────────────────────────────────────────────────────────────────────────
# Static recipe example bank
# Extend this as you add more cuisines and goals
# ─────────────────────────────────────────────────────────────────────────────

RECIPE_BANK: list[RecipeContext] = [

    # ── Pakistani ────────────────────────────────────────────────────────────
    RecipeContext(
        dish_name="Chicken Karahi",
        cuisine="pakistani",
        goal_fit="muscle_gain",
        key_proteins=["chicken"],
        approx_calories=520,
        notes="High protein, medium fat from oil. Serve with 1 roti for carbs.",
    ),
    RecipeContext(
        dish_name="Daal Mash with Brown Rice",
        cuisine="pakistani",
        goal_fit="maintenance",
        key_proteins=["urad lentils"],
        approx_calories=420,
        notes="Plant-based protein, complex carbs, low fat. Good fiber content.",
    ),
    RecipeContext(
        dish_name="Grilled Tandoori Chicken with Raita",
        cuisine="pakistani",
        goal_fit="fat_loss",
        key_proteins=["chicken breast"],
        approx_calories=350,
        notes="Lean protein, minimal oil, yogurt raita adds probiotics. "
              "Skip naan — serve with salad.",
    ),
    RecipeContext(
        dish_name="Keema Methi with Chapati",
        cuisine="pakistani",
        goal_fit="muscle_gain",
        key_proteins=["ground beef", "fenugreek leaves"],
        approx_calories=580,
        notes="Dense protein + iron from beef. Fenugreek aids digestion.",
    ),

    # ── Indian ───────────────────────────────────────────────────────────────
    RecipeContext(
        dish_name="Paneer Tikka with Mint Chutney",
        cuisine="indian",
        goal_fit="muscle_gain",
        key_proteins=["paneer"],
        approx_calories=450,
        notes="High protein vegetarian option. Grill, don't fry. "
              "Good for lacto-vegetarians.",
    ),
    RecipeContext(
        dish_name="Dal Tadka with Brown Rice",
        cuisine="indian",
        goal_fit="maintenance",
        key_proteins=["toor dal"],
        approx_calories=400,
        notes="Balanced plant protein + complex carbs. "
              "Add a teaspoon of ghee for healthy fat.",
    ),
    RecipeContext(
        dish_name="Chicken Tikka Salad",
        cuisine="indian",
        goal_fit="fat_loss",
        key_proteins=["chicken breast"],
        approx_calories=310,
        notes="Low calorie, high protein. Skip the rice, add cucumber and tomato.",
    ),

    # ── Italian ──────────────────────────────────────────────────────────────
    RecipeContext(
        dish_name="Grilled Salmon Pasta",
        cuisine="italian",
        goal_fit="muscle_gain",
        key_proteins=["salmon"],
        approx_calories=620,
        notes="Omega-3 rich protein + complex carbs from pasta. Use whole wheat pasta.",
    ),
    RecipeContext(
        dish_name="Chicken Breast with Zucchini and Tomato Sauce",
        cuisine="italian",
        goal_fit="fat_loss",
        key_proteins=["chicken breast"],
        approx_calories=330,
        notes="Low carb, high protein. No pasta. Good for aggressive fat loss.",
    ),

    # ── Chinese ──────────────────────────────────────────────────────────────
    RecipeContext(
        dish_name="Stir-Fried Tofu with Vegetables and Brown Rice",
        cuisine="chinese",
        goal_fit="maintenance",
        key_proteins=["tofu"],
        approx_calories=380,
        notes="Plant-based, balanced macros. Low sodium if using low-sodium soy sauce.",
    ),
    RecipeContext(
        dish_name="Steamed Fish with Ginger and Spring Onion",
        cuisine="chinese",
        goal_fit="fat_loss",
        key_proteins=["white fish"],
        approx_calories=280,
        notes="Very lean protein. Minimal oil. Classic steaming preserves nutrients.",
    ),

    # ── Any / Generic ─────────────────────────────────────────────────────────
    RecipeContext(
        dish_name="Egg White Omelette with Spinach and Feta",
        cuisine="any",
        goal_fit="fat_loss",
        key_proteins=["egg whites"],
        approx_calories=250,
        notes="Ultra-lean breakfast. High protein, very low fat and carbs.",
    ),
    RecipeContext(
        dish_name="Oats with Banana and Peanut Butter",
        cuisine="any",
        goal_fit="muscle_gain",
        key_proteins=["oats", "peanut butter"],
        approx_calories=520,
        notes="Pre-workout meal. Slow carbs + protein + healthy fat.",
    ),
    RecipeContext(
        dish_name="Grilled Chicken with Sweet Potato and Broccoli",
        cuisine="any",
        goal_fit="muscle_gain",
        key_proteins=["chicken breast"],
        approx_calories=550,
        notes="Classic bodybuilder plate. Clean macros, easy to portion.",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval function
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_context(
    goal_type: str,
    cuisine: str,
    n: int = 2,
) -> list[RecipeContext]:
    """
    Retrieve n most relevant recipe examples.

    Priority:
    1. Exact cuisine + goal match
    2. Goal match only (any cuisine)
    3. "any" cuisine + goal match

    Phase 3: replace this with vector similarity search.
    """
    cuisine_lower = (cuisine or "any").lower()

    # Exact match first
    exact = [
        r for r in RECIPE_BANK
        if r.goal_fit == goal_type
        and (r.cuisine == cuisine_lower or cuisine_lower in r.cuisine)
    ]

    if len(exact) >= n:
        return exact[:n]

    # Fall back to any cuisine with same goal
    fallback = [
        r for r in RECIPE_BANK
        if r.goal_fit == goal_type and r.cuisine == "any"
    ]

    combined = exact + fallback
    return combined[:n] if len(combined) >= n else combined