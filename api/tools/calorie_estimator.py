# tools/calorie_estimator.py

from langchain.tools import Tool

# 📦 Basic calorie database (expandable)
CALORIE_DB = {
    "chicken breast": 165,
    "brown rice": 111,
    "broccoli": 35,
    "olive oil": 119,
    "egg": 78,
    "banana": 89,
    "apple": 95,
    "sweet potato": 103,
    "salmon": 208,
    "tofu": 76,
    "almonds": 164,
    # Add more as needed
}

def estimate_calories(ingredients: list) -> dict:
    """
    Estimate total calories from ingredients.
    Each ingredient should be a string like "1 cup brown rice" or "100g chicken breast".
    """
    total_calories = 0
    details = []

    for item in ingredients:
        item_lower = item.lower()
        found = False

        for food, cal in CALORIE_DB.items():
            if food in item_lower:
                found = True
                quantity_multiplier = 1

                # Simple multiplier logic (not perfect, just a placeholder)
                if "100g" in item_lower or "1 serving" in item_lower or "1 piece" in item_lower:
                    quantity_multiplier = 1
                elif "2" in item_lower:
                    quantity_multiplier = 2
                elif "3" in item_lower:
                    quantity_multiplier = 3

                item_cal = cal * quantity_multiplier
                total_calories += item_cal
                details.append(f"{item} ≈ {item_cal} kcal")
                break

        if not found:
            details.append(f"{item} = ❓ Unknown item (not found in DB)")

    return {
        "estimated_calories": int(total_calories),
        "calorie_breakdown": details
    }

# ✅ LangChain Tool wrapper
calorie_estimator_tool = Tool(
    name="CalorieEstimator",
    func=lambda args: estimate_calories(args["ingredients"]),
    description="Estimates calories from a list of ingredients with quantities."
)
