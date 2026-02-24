# tools/allergen_checker.py

from langchain.tools import Tool

# ✅ Basic substitution dictionary (extend as needed)
SAFE_SUBSTITUTES = {
    "peanuts": "sunflower seeds",
    "milk": "almond milk",
    "egg": "chia seeds (as egg replacer)",
    "wheat": "gluten-free flour",
    "shrimp": "tofu",
    "soy": "lentils",
    "almonds": "pumpkin seeds",
    "cheese": "vegan cheese"
}

def check_allergens(ingredients: list, allergies: list, preferences: list) -> dict:
    flagged = []
    substitutions = {}

    for item in ingredients:
        for allergen in allergies + preferences:
            if allergen.lower() in item.lower():
                flagged.append(item)
                substitute = SAFE_SUBSTITUTES.get(allergen.lower())
                if substitute:
                    substitutions[item] = substitute

    return {
        "conflicts_found": len(flagged) > 0,
        "flagged_ingredients": flagged,
        "suggested_substitutes": substitutions
    }

# ✅ LangChain Tool wrapper
allergen_checker_tool = Tool(
    name="AllergenChecker",
    func=lambda args: check_allergens(args["ingredients"], args["allergies"], args["preferences"]),
    description="Checks ingredients for allergens or disliked items and suggests safe substitutions if found."
)
