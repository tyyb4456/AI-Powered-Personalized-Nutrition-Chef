"""
agents/followup_agent.py

Follow-up agent — handles user prompts AFTER a recipe has been generated.

Responsibilities:
  1. CLASSIFY intent: is the user asking a QUESTION or requesting a MODIFICATION?
  2. Route accordingly:
     - "question"  → answer directly using the current recipe context (no regeneration)
     - "modify"    → inject the user's instruction into NutritionState so the pipeline
                     can regenerate from recipe_generator_node onward
     - "done"      → user is satisfied; signal the service layer to stop

The node returns only the keys it modifies:
  - followup_intent        : "question" | "modify" | "done"
  - followup_answer        : populated for "question" intent only
  - followup_history       : appended every turn (question + answer/ack)
  - followup_modification  : plain-English instruction injected into recipe_generator_node
                             (e.g. "make it vegan", "reduce calories by 200")
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from state import NutritionState

load_dotenv()
logger = logging.getLogger(__name__)

# ── LLM setup ─────────────────────────────────────────────────────────────────

_model = init_chat_model("google_genai:gemini-2.5-flash")


# ── Structured output schemas ──────────────────────────────────────────────────

class IntentClassification(BaseModel):
    intent: Literal["question", "modify", "done"] = Field(
        ...,
        description=(
            "'question'  — user is asking something about the existing recipe "
            "(nutrition, ingredients, steps, substitutions, storage, etc.).\n"
            "'modify'    — user wants the recipe changed or regenerated differently "
            "(different cuisine, fewer calories, add/remove ingredients, etc.).\n"
            "'done'      — user is satisfied and has no more requests."
        ),
    )
    reasoning: str = Field(..., description="One-sentence explanation of why you chose this intent.")


class QuestionAnswer(BaseModel):
    answer: str = Field(..., description="Clear, helpful answer to the user's question about the recipe.")


class ModificationInstruction(BaseModel):
    instruction: str = Field(
        ...,
        description=(
            "A concise, self-contained instruction for regenerating the recipe. "
            "Must include any relevant context from the current recipe so the "
            "generator doesn't need to re-read history. "
            "Example: 'Regenerate as a vegan dish with the same calorie target. "
            "Original was a chicken tikka masala.'"
        ),
    )


# ── Prompts ────────────────────────────────────────────────────────────────────

_INTENT_PROMPT = ChatPromptTemplate.from_template("""
You are a classifier for a nutrition AI app.

The user just received a generated recipe and sent a follow-up message.
Classify the intent of their message as one of:
  - "question"  : they are asking about the current recipe
  - "modify"    : they want the recipe changed or a new one generated
  - "done"      : they are satisfied and done

Current recipe: {dish_name}
User message: "{user_prompt}"

Return your classification as JSON.
""")

_QA_PROMPT = ChatPromptTemplate.from_template("""
You are a helpful nutrition and cooking assistant.

The user has been given this recipe and has a question about it.

Recipe: {dish_name}
Cuisine: {cuisine}
Meal type: {meal_type}
Calories: {calories} kcal | Protein: {protein_g}g | Carbs: {carbs_g}g | Fat: {fat_g}g

Ingredients:
{ingredients}

Steps:
{steps}

Explanation (why this recipe was chosen): {explanation}

Conversation history:
{history}

User's question: "{user_prompt}"

Answer clearly and concisely. If the question is about health, nutrition, or 
ingredient substitutions, be specific and accurate.
""")

_MODIFY_PROMPT = ChatPromptTemplate.from_template("""
You are helping a nutrition AI understand how to regenerate a recipe.

The user received this recipe:
  Dish: {dish_name}
  Cuisine: {cuisine}
  Calories: {calories} kcal

They now want a change: "{user_prompt}"

Write a single, self-contained modification instruction that the recipe 
generator can use to produce an improved recipe. Be specific about what 
should change and what should stay the same.
""")


# ── LLMs with structured output ───────────────────────────────────────────────

_intent_llm   = _model.with_structured_output(IntentClassification)
_qa_llm       = _model.with_structured_output(QuestionAnswer)
_modify_llm   = _model.with_structured_output(ModificationInstruction)


# ── Helper: serialise recipe for prompts ──────────────────────────────────────

def _fmt_ingredients(recipe) -> str:
    return "\n".join(f"  - {i.quantity} {i.name}" for i in recipe.ingredients)


def _fmt_steps(recipe) -> str:
    return "\n".join(f"  {n+1}. {s}" for n, s in enumerate(recipe.steps))


def _fmt_history(history: list[str]) -> str:
    return "\n".join(history) if history else "None"


# ── Main node ─────────────────────────────────────────────────────────────────

def followup_agent_node(state: NutritionState) -> dict:
    """
    LangGraph node — called after explainability_agent_node.

    Reads:  state.followup_prompt, state.final_recipe, state.followup_history
    Writes: state.followup_intent, state.followup_answer,
            state.followup_history, state.followup_modification
    """
    user_prompt = (state.followup_prompt or "").strip()
    recipe      = state.final_recipe
    history     = list(state.followup_history or [])

    if not user_prompt:
        logger.warning("followup_agent_node called with no followup_prompt — skipping.")
        return {"followup_intent": "done"}

    if not recipe:
        logger.warning("followup_agent_node called but no final_recipe in state.")
        return {
            "followup_intent":  "question",
            "followup_answer":  "I don't have a recipe in context yet. Please generate one first.",
            "followup_history": history,
        }

    dish_name = recipe.dish_name
    print(f"\n💬 Follow-up received: '{user_prompt}'")

    # ── Step 1: Classify intent ────────────────────────────────────────────────
    intent_result: IntentClassification = _intent_llm.invoke(
        _INTENT_PROMPT.format_messages(
            dish_name   = dish_name,
            user_prompt = user_prompt,
        )
    )
    intent = intent_result.intent
    print(f"   🔍 Intent classified as: '{intent}' ({intent_result.reasoning})")

    updates: dict = {"followup_intent": intent}

    # ── Step 2: Handle each intent ────────────────────────────────────────────

    if intent == "question":
        qa_result: QuestionAnswer = _qa_llm.invoke(
            _QA_PROMPT.format_messages(
                dish_name   = dish_name,
                cuisine     = recipe.cuisine     or "not specified",
                meal_type   = recipe.meal_type   or "not specified",
                calories    = recipe.nutrition.calories,
                protein_g   = recipe.nutrition.protein_g,
                carbs_g     = recipe.nutrition.carbs_g,
                fat_g       = recipe.nutrition.fat_g,
                ingredients = _fmt_ingredients(recipe),
                steps       = _fmt_steps(recipe),
                explanation = state.recipe_explanation or "N/A",
                history     = _fmt_history(history),
                user_prompt = user_prompt,
            )
        )
        answer = qa_result.answer
        print(f"   💡 Answer: {answer[:120]}{'...' if len(answer) > 120 else ''}")

        history.append(f"User: {user_prompt}")
        history.append(f"Assistant: {answer}")

        updates["followup_answer"]  = answer
        updates["followup_history"] = history

    elif intent == "modify":
        modify_result: ModificationInstruction = _modify_llm.invoke(
            _MODIFY_PROMPT.format_messages(
                dish_name   = dish_name,
                cuisine     = recipe.cuisine or "not specified",
                calories    = recipe.nutrition.calories,
                user_prompt = user_prompt,
            )
        )
        instruction = modify_result.instruction
        print(f"   🔧 Modification instruction: {instruction[:120]}{'...' if len(instruction) > 120 else ''}")

        history.append(f"User: {user_prompt}")
        history.append(f"Assistant: [Regenerating recipe — {instruction}]")

        updates["followup_modification"] = instruction
        updates["followup_history"]      = history

        # Clear previous recipe state so recipe_generator_node runs fresh
        updates["generated_recipe"]       = None
        updates["recipe_generated"]       = False
        updates["validation_passed"]      = None
        updates["validation_result"]      = None
        updates["validation_notes"]       = None
        updates["substitution_output"]    = None
        updates["substitutions_made"]     = False
        updates["adjusted_by_macro_agent"] = False
        updates["macro_adjustment_output"] = None
        updates["final_recipe"]           = None
        updates["recipe_explanation"]     = None
        updates["retry_count"]            = 0

    elif intent == "done":
        history.append(f"User: {user_prompt}")
        history.append("Assistant: [Session ended]")
        updates["followup_history"] = history
        print("   ✅ User is done. Ending follow-up loop.")

    return updates