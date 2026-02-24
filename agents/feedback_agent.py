from state import NutritionState

def feedback_agent_node(state: NutritionState) -> NutritionState:
    print("\n🧪 Collecting feedback on the meal...")

    # Simulated feedback – replace with UI input in production
    print("\nHow would you rate this recipe (1–5)?")
    rating = int(input("⭐ Rating: "))

    print("Any comments or suggestions?")
    comment = input("📝 Comment: ")

    return state.copy(update={
        "feedback_rating": rating,
        "feedback_comment": comment,
        "feedback_collected": True
    })
