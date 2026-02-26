"""
agents/learning_loop_agent.py
"""

from state import NutritionState
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")

with open("prompts/learning_prompt.txt", "r", encoding="utf-8") as f:
    raw_prompt = f.read()

learning_prompt = ChatPromptTemplate.from_template(raw_prompt)


def learning_loop_agent_node(state: NutritionState) -> dict:
    print("\n🔁 Learning from feedback...")

    messages = learning_prompt.format_messages(
        rating=state.feedback_rating,
        comment=state.feedback_comment or "No comment.",
        preferences=state.preferences,
        goal=state.fitness_goal,
    )

    response = model.invoke(messages)

    return {
        "learned_preferences": {"insights": response.content},
        "updated_goals": state.fitness_goal,
    }