from state import NutritionState
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 💬 LLM Setup (Groq + DeepSeek LLaMA)
llm = ChatGroq(
    model="meta-llama/llama-4-maverick-17b-128e-instruct",
    temperature=0.5
)

with open("prompts/substitution_prompt.txt", "r", encoding="utf-8") as file:
    raw_prompt = file.read()

prompt_template = ChatPromptTemplate.from_template(raw_prompt)

def substitution_agent_node(state: NutritionState) -> NutritionState:
    print("\n🔄 Checking recipe for conflicts and suggesting substitutions...")

    prompt = prompt_template.format_messages(
        allergies=state.allergies or [],
        preferences=state.preferences or {},
        recipe=state.generated_recipe,
    )

    response = llm.invoke(prompt)
    revised = response.content

    substitutions_found = "substitute" in revised.lower() or "revised recipe" in revised.lower()

    state = {
        "revised_recipe": revised if substitutions_found else state.generated_recipe,
        "substitutions_made": substitutions_found
    }

    return state
