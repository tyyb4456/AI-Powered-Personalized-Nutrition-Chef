# tools/goal_recommender.py

from langchain.tools import Tool

def recommend_goal(profile: dict) -> str:
    """
    Simple rule-based goal recommender. Replace with LLM logic later if needed.
    """

    age = profile.get("age", 25)
    weight = profile.get("weight", 70)  # in kg
    height = profile.get("height", 170)  # in cm
    activity = profile.get("activity_level", "moderate")
    goal = profile.get("personal_goal", "").lower()

    bmi = (weight / ((height / 100) ** 2))

    if "lose" in goal or "fat" in goal or bmi > 27:
        return "Fat Loss"
    elif "muscle" in goal or "gain" in goal or "bulk" in goal:
        return "Muscle Gain"
    elif "endurance" in goal:
        return "Endurance Training"
    elif 18.5 <= bmi <= 24.9:
        return "Maintenance"
    elif 25 <= bmi < 27 and activity == "high":
        return "Clean Bulking"
    else:
        return "Maintenance"

# ✅ LangChain Tool wrapper
goal_recommender_tool = Tool(
    name="GoalRecommender",
    func=lambda args: recommend_goal(args),
    description="Analyzes a user profile and recommends a suitable fitness goal like Fat Loss, Muscle Gain, Maintenance, etc."
)
