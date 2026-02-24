from graph_builder import graph
from state import NutritionState

if __name__ == "__main__":
    print("🍽️ Starting Personalized Nutrition Chef...\n")
    raw_state = graph.invoke(NutritionState())
    
    # Convert to NutritionState
    final_state = NutritionState(**raw_state)

    print("\n🍳 Final Personalized Recipe:\n")
    print(final_state.generated_recipe)
    print("\n----------------------------------------------------\n")
    print("\n📊 Nutrition Information:\n")
    if final_state.recipe_nutrition:
        for nutrient, value in final_state.recipe_nutrition.items():
            print(f"{nutrient.capitalize()}: {value}")
    else:
        print("No nutrition information available.")

    print("\n----------------------------------------------------\n")

    print("revise recipe:\n\n", final_state.revised_recipe)

    print("\n----------------------------------------------------\n")

    print("explanation:\n\n", final_state.recipe_explanation)



# from tools.macro_calculator import macro_calculator_tool

# input_data = {
#     "age": 25,
#     "gender": "male",
#     "weight": 70,
#     "height": 175,
#     "activity_level": "moderate",
#     "goal": "gain muscle"
# }

# result = macro_calculator_tool.func(input_data)
# print("Macro Calculator Result:")
# print(result)

# from tools.calorie_estimator import calorie_estimator_tool

# result = calorie_estimator_tool.func({
#     "ingredients": [
#         "100g chicken breast",
#         "1 cup brown rice",
#         "1 tbsp olive oil",
#         "1 cup broccoli"
#     ]
# })

# print(result)

# from tools.allergen_checker import allergen_checker_tool

# result = allergen_checker_tool.func({
#     "ingredients": [
#         "peanut butter",
#         "whole wheat bread",
#         "cheddar cheese",
#         "egg"
#     ],
#     "allergies": ["peanuts", "egg"],
#     "preferences": ["cheese"]
# })

# print(result)

# from tools.goal_recommender import goal_recommender_tool

# user_profile = {
#     "age": 28,
#     "weight": 55,
#     "height": 172,
#     "activity_level": "low",
#     "personal_goal": "YES"
# }

# recommended = goal_recommender_tool.func(user_profile)
# print(f"🎯 Suggested Fitness Goal: {recommended}")


