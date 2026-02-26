"""
agents/grocery_agent.py

Takes the full MealPlan and produces a smart GroceryList.

Steps:
1. Extract all ingredients from all recipes in the meal plan
2. Consolidate duplicates (same ingredient, sum quantities where possible)
3. Categorise each item (produce / protein / dairy / pantry / spices / frozen)
4. Estimate cost in PKR using a local price reference table
5. Identify bulk-buy opportunities (used 3+ times across the week)
6. Return structured GroceryList

Cost estimation uses a static PKR price table.
Phase 4: replace with a live supermarket API integration.
"""

from __future__ import annotations

import re
from collections import defaultdict

from state import WeeklyPlanState
from schemas.nutrition_schemas import GroceryList, GroceryItem
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")
llm   = model.with_structured_output(GroceryList)

# ── PKR Price Reference Table (per 100g or per unit) ─────────────────────────
# Approximate Lahore market prices (2025)
PKR_PRICES: dict[str, tuple[float, str]] = {
    # (price_per_unit, unit_description)
    "chicken breast":  (85.0,  "per 100g"),
    "chicken":         (70.0,  "per 100g"),
    "beef":            (120.0, "per 100g"),
    "ground beef":     (110.0, "per 100g"),
    "salmon":          (250.0, "per 100g"),
    "fish":            (90.0,  "per 100g"),
    "eggs":            (20.0,  "per egg"),
    "egg":             (20.0,  "per egg"),
    "milk":            (160.0, "per litre"),
    "yogurt":          (60.0,  "per 100g"),
    "paneer":          (150.0, "per 100g"),
    "cheese":          (200.0, "per 100g"),
    "brown rice":      (30.0,  "per 100g"),
    "white rice":      (20.0,  "per 100g"),
    "oats":            (25.0,  "per 100g"),
    "whole wheat flour": (18.0, "per 100g"),
    "sweet potato":    (40.0,  "per 100g"),
    "potato":          (25.0,  "per 100g"),
    "broccoli":        (80.0,  "per 100g"),
    "spinach":         (30.0,  "per 100g"),
    "tomato":          (20.0,  "per 100g"),
    "onion":           (15.0,  "per 100g"),
    "garlic":          (40.0,  "per 100g"),
    "ginger":          (35.0,  "per 100g"),
    "lemon":           (10.0,  "per piece"),
    "banana":          (15.0,  "per piece"),
    "apple":           (30.0,  "per piece"),
    "olive oil":       (4.0,   "per ml"),
    "cooking oil":     (2.0,   "per ml"),
    "lentils":         (22.0,  "per 100g"),
    "chickpeas":       (28.0,  "per 100g"),
    "tofu":            (120.0, "per 100g"),
    "almond milk":     (3.0,   "per ml"),
    "peanut butter":   (180.0, "per 100g"),
    "almonds":         (300.0, "per 100g"),
}

# ── Category mapping ──────────────────────────────────────────────────────────
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "protein": [
        "chicken", "beef", "fish", "salmon", "tuna", "eggs", "egg",
        "paneer", "tofu", "lentils", "chickpeas", "dal",
    ],
    "dairy": [
        "milk", "yogurt", "cheese", "cream", "butter", "ghee",
        "almond milk", "oat milk",
    ],
    "produce": [
        "spinach", "broccoli", "tomato", "onion", "garlic", "ginger",
        "pepper", "zucchini", "carrot", "cucumber", "lettuce",
        "methi", "fenugreek", "coriander", "mint", "banana", "apple",
        "lemon", "lime", "potato", "sweet potato",
    ],
    "pantry": [
        "rice", "oats", "flour", "pasta", "bread", "oil", "olive oil",
        "peanut butter", "almonds", "nuts", "seeds",
        "soy sauce", "vinegar", "honey", "sugar",
    ],
    "spices": [
        "salt", "pepper", "cumin", "coriander", "turmeric", "chili",
        "garam masala", "paprika", "cardamom", "cinnamon", "clove",
    ],
    "frozen": ["frozen", "ice cream"],
}


def _categorise(ingredient_name: str) -> str:
    name_lower = ingredient_name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return category
    return "pantry"


def _estimate_cost(ingredient_name: str, quantity: str) -> Optional[float]:
    """Very rough PKR cost estimate."""
    name_lower = ingredient_name.lower()
    for key, (price, _) in PKR_PRICES.items():
        if key in name_lower:
            # Try to extract a numeric quantity
            nums = re.findall(r"[\d.]+", quantity)
            if nums:
                amount = float(nums[0])
                return round(price * amount / 100, 0)   # normalise per 100g
    return None


# ── LLM Prompt ────────────────────────────────────────────────────────────────
GROCERY_PROMPT = ChatPromptTemplate.from_template("""
You are a smart grocery planning assistant.

Consolidate the following ingredient list from a 7-day meal plan into an
optimised shopping list.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ALL INGREDIENTS (across all meals)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{all_ingredients}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Merge duplicate ingredients — sum their quantities into one line
   (e.g. "200g chicken breast" + "300g chicken breast" → "500g chicken breast")
2. Assign each item a category: produce / protein / dairy / pantry / spices / frozen
3. For items appearing 3 or more times across the week, add a bulk_buy_tip
   (e.g. "Buy 1kg pack — used 5x this week")
4. Estimate cost in PKR where possible (use realistic Lahore market prices 2025)
5. Add overall shopping_notes (best day to shop, freshness tips, etc.)
6. Set total_items = number of unique items

Currency: Pakistani Rupees (PKR)
""")


def grocery_agent_node(state: WeeklyPlanState) -> dict:
    print("\n🛒 Generating grocery list...")

    if not state.meal_plan:
        return {"pipeline_error": "GroceryAgent: no meal_plan in state."}

    # ── Collect all ingredients from all meals ────────────────────────────────
    ingredient_counts: dict[str, int] = defaultdict(int)
    all_lines: list[str] = []

    for day_plan in state.meal_plan.days:
        for meal_slot in day_plan.meals:
            for ing in meal_slot.recipe.ingredients:
                key = ing.name.lower().strip()
                ingredient_counts[key] += 1
                all_lines.append(f"- {ing.quantity} {ing.name} (from: {meal_slot.recipe.dish_name})")

    print(f"   Collected {len(all_lines)} ingredient lines across the week")

    messages = GROCERY_PROMPT.format_messages(
        all_ingredients="\n".join(all_lines),
    )

    grocery_list: GroceryList = llm.invoke(messages)

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"✅ Grocery list: {grocery_list.total_items} unique items")
    if grocery_list.estimated_total_cost_pkr:
        print(f"   Estimated total: PKR {grocery_list.estimated_total_cost_pkr:,.0f}")

    by_cat = grocery_list.by_category()
    for cat, items in by_cat.items():
        print(f"   {cat.capitalize()}: {len(items)} items")

    return {
        "grocery_list":      grocery_list,
        "grocery_generated": True,
    }

