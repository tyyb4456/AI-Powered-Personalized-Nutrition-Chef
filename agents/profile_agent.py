from state import NutritionState

def profile_agent_node(state: NutritionState) -> NutritionState:
    print("\n👤 Collecting Customer Profile...")

    # 🧾 Input Collection (UI/API will replace later)
    name = input("Enter customer name: ").strip()
    while not name:
        name = input("⚠️ Name cannot be empty. Please enter customer name: ").strip()

    try:
        age = int(input("Enter age: ").strip())
    except ValueError:
        print("⚠️ Invalid input. Setting age to 25 by default.")
        age = 25

    allergies_input = input("List any allergies (comma-separated, or 'none'): ").strip()
    allergies = [a.strip() for a in allergies_input.split(',')] if allergies_input.lower() != 'none' else []

    fitness_goal = input("Fitness goal (e.g., muscle gain, weight loss, maintenance): ").strip()
    while not fitness_goal:
        fitness_goal = input("⚠️ Please specify a fitness goal: ").strip()

    spice_level = input("Preferred spice level (Low, Medium, High): ").strip().capitalize()
    if spice_level not in ["Low", "Medium", "High"]:
        print("⚠️ Invalid choice. Defaulting to 'Medium'")
        spice_level = "Medium"

    cuisine = input("Preferred cuisine (e.g., Italian, Indian, Chinese): ").strip()
    if not cuisine:
        cuisine = "Indian"

    preferences = {
        "spice_level": spice_level,
        "cuisine": cuisine
    }

    # print("\n✅ Profile Captured:")
    # print({
    #     "name": name,
    #     "age": age,
    #     "allergies": allergies,
    #     "fitness_goal": fitness_goal,
    #     "preferences": preferences
    # })

    return NutritionState(
        name=name,
        age=age,
        allergies=allergies,
        preferences=preferences,
        fitness_goal=fitness_goal,
        profile_collected=True,

    )
