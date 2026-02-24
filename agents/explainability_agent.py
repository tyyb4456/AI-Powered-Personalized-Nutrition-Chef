from state import NutritionState
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv

load_dotenv()

# 💬 LLM Setup (Groq + DeepSeek LLaMA)
llm = ChatGroq(
    model="deepseek-r1-distill-llama-70b",
    temperature=0.5
)

explanation_prompt = ChatPromptTemplate.from_template("""
You are an AI Nutrition Assistant.

Explain why the following recipe was selected for the user, based on:
1. Their fitness goal: {fitness_goal}
2. Calorie target: {calorie_target}
3. Macronutrient distribution: {macro_split}
4. Preferences: {preferences}
5. Allergies: {allergies}
6. Substitutions made: {substitutions_made}

Recipe:
{recipe}
""")

def explainability_agent_node(state: NutritionState) -> NutritionState:
    print("\n🧠 Explaining recipe selection...")

    recipe_to_explain = state.revised_recipe if state.substitutions_made else state.generated_recipe

    prompt = explanation_prompt.format_messages(
        fitness_goal=state.fitness_goal,
        calorie_target=state.calorie_target,
        macro_split=state.macro_split,
        preferences=state.preferences,
        allergies=state.allergies,
        substitutions_made=state.substitutions_made,
        recipe=recipe_to_explain
    )

    response = llm.invoke(prompt)
    explanation = response.content

    return {
        "recipe_explanation": explanation
    }