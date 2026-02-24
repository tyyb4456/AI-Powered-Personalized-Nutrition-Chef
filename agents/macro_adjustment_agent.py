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
from pathlib import Path

with open("prompts/macro_adjustment.txt", "r", encoding="utf-8") as file:
    raw_prompt = file.read()

macro_prompt_template = ChatPromptTemplate.from_template(raw_prompt)


def macro_adjustment_agent_node(state: NutritionState) -> NutritionState:
    print("\n🛠️ Adjusting macros to optimize the recipe...")

    inputs = {
        "fitness_goal": state.fitness_goal,
        "calorie_target": state.calorie_target,
        "macro_split": state.macro_split,
        "recipe_nutrition": state.recipe_nutrition,
        "recipe": state.recipe,
        "allergies": state.allergies
    }

    chain = macro_prompt_template | llm
    response = chain.invoke(inputs).content.strip()

    # You can parse out new nutrition estimates if needed (later)

    state = {
        "recipe": response,
        "adjusted_by_macro_agent": True
    }
    
    return state
