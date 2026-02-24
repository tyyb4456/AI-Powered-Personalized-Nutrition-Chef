from state import NutritionState

def health_goal_agent_node(state: NutritionState) -> NutritionState:
    print("\n💪 Interpreting fitness goal into dietary requirements...")

    goal = (state.fitness_goal or "").lower()

    if not goal:
        print("⚠️ No fitness goal provided. Defaulting to 'maintenance'.")
        goal = "maintenance"

    # 🎯 Match goal to dietary plan
    if "muscle" in goal or "gain" in goal or "bulk" in goal:
        calorie_target = 2800
        macro_split = {"protein": 40, "carbs": 35, "fat": 25}
        profile_type = "High-protein for muscle gain"
    elif "loss" in goal or "cut" in goal or "fat" in goal:
        calorie_target = 1800
        macro_split = {"protein": 30, "carbs": 30, "fat": 40}
        profile_type = "Low-calorie for fat loss"
    else:  # Maintenance or unclear goals
        calorie_target = 2200
        macro_split = {"protein": 30, "carbs": 40, "fat": 30}
        profile_type = "Balanced for maintenance"

    print(f"✅ Goal interpreted as: {profile_type}")
    print(f"🍽️ Calories: {calorie_target} | Macros: {macro_split}")

    state = {
        "calorie_target": calorie_target,
        "macro_split": macro_split,
        "goal_interpreted": True
    }
    
    return state