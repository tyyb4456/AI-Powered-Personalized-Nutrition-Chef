# tools/macro_calculator.py

from langchain.tools import Tool

def calculate_macros(age: int, gender: str, weight: float, height: float, activity_level: str, goal: str) -> dict:
    """
    Calculate calorie needs and macro breakdown.
    weight in kg, height in cm
    """

    # 1️⃣ BMR Calculation (Mifflin-St Jeor Equation)
    if gender.lower() == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    # 2️⃣ Activity Factor
    activity_factors = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very active": 1.9,
    }
    factor = activity_factors.get(activity_level.lower(), 1.2)
    maintenance_calories = bmr * factor

    # 3️⃣ Goal Adjustment
    if goal == "lose fat":
        target_calories = maintenance_calories - 500
    elif goal == "gain muscle":
        target_calories = maintenance_calories + 300
    else:
        target_calories = maintenance_calories

    # 4️⃣ Macro Split (simple rules)
    protein_ratio = 0.3
    carb_ratio = 0.4
    fat_ratio = 0.3

    protein = (target_calories * protein_ratio) / 4
    carbs = (target_calories * carb_ratio) / 4
    fats = (target_calories * fat_ratio) / 9

    return {
        "target_calories": int(target_calories),
        "macros": {
            "protein_g": int(protein),
            "carbs_g": int(carbs),
            "fat_g": int(fats)
        }
    }

# ✅ Wrap as a LangChain Tool
macro_calculator_tool = Tool(
    name="MacroCalculator",
    func=lambda args: calculate_macros(**args),
    description="Calculates daily calorie target and macro breakdown based on user info."
)
