from state import NutritionState
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from dotenv import load_dotenv

load_dotenv()

# 💬 LLM Setup (Groq + DeepSeek LLaMA)
llm = ChatGroq(
    model="deepseek-r1-distill-llama-70b",
    temperature=0.5
)

with open("prompts/recipe_generation.txt", "r", encoding="utf-8") as file:
    raw_prompt = file.read()

prompt_template = ChatPromptTemplate.from_template(raw_prompt)

def recipe_generator_node(state: NutritionState) -> NutritionState:
    print("\n🍽️ Generating personalized recipe...")

    messages = prompt_template.format_messages(
        age=state.age,
        fitness_goal=state.fitness_goal,
        calorie_target=state.calorie_target,
        macro_split=state.macro_split,
        preferences=state.preferences,
        allergies=state.allergies
    )

    response = llm.invoke(messages)
    recipe = response.content

    state = {
        "generated_recipe": recipe,
        "recipe_nutrition": {
            "estimated_calories": state.calorie_target,
            "macro_split": state.macro_split
        },
        "recipe_generated": True
    }

    return state
