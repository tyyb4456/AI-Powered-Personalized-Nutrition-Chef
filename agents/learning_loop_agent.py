from state import NutritionState
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv

load_dotenv()

# 💬 LLM Setup (Groq + DeepSeek LLaMA)
llm = ChatGroq(
    model="meta-llama/llama-4-maverick-17b-128e-instruct",
    temperature=0.5
)

learning_prompt = ChatPromptTemplate.from_template("""
You are a Learning Agent in an AI chef system.

Based on the user feedback below, extract insights to improve future meals.

Feedback:
Rating: {rating}
Comment: {comment}

User preferences: {preferences}
Original goal: {goal}

Return:
- Updated preferences
- Adjusted interpretation of the user's fitness goal (if necessary)
""")

def learning_loop_agent_node(state: NutritionState) -> NutritionState:
    print("\n🔁 Learning from feedback to adapt future recommendations...")

    prompt = learning_prompt.format_messages(
        rating=state.feedback_rating,
        comment=state.feedback_comment,
        preferences=state.preferences,
        goal=state.fitness_goal
    )

    response = llm.invoke(prompt)
    insights = response.content

    state = {
        "learned_preferences": {"insights": insights},
        "updated_goals": state.fitness_goal  # Future: could adapt this
    }

    return state 