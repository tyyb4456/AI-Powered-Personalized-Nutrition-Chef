"""
agents/feedback_agent.py
"""

from state import NutritionState


def feedback_agent_node(state: NutritionState) -> dict:
    print("\n🧪 Collecting feedback on the meal...")

    while True:
        try:
            rating = int(input("⭐ Rate the recipe (1–5): ").strip())
            if 1 <= rating <= 5:
                break
            print("   ⚠️ Please enter a number between 1 and 5.")
        except ValueError:
            print("   ⚠️ Invalid input. Enter a number.")

    comment = input("📝 Any comments or suggestions? ").strip()

    return {
        "feedback_rating":   rating,
        "feedback_comment":  comment,
        "feedback_collected": True,
    }