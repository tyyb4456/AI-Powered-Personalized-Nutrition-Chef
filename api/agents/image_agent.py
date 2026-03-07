"""
agents/image_agent.py

Food Image Recognition Agent — Phase 3 premium feature.

Uses Gemini 2.0 Flash's native vision capability (no GPT-4o needed —
you're already on gemini-2.5-flash which supports image input).

Flow:
1. User provides image path (CLI) or base64 string (future API)
2. Image is loaded and sent to Gemini vision with a structured prompt
3. LLM returns FoodImageAnalysis (identified items + estimated nutrition)
4. Result is packaged as a MealLogEntry ready to be committed
5. User confirms before logging

Supported formats: JPEG, PNG, WEBP
"""

from __future__ import annotations

import base64
import os
from datetime import date
from pathlib import Path

import google as genai
from dotenv import load_dotenv

from state import NutritionState
from schemas.nutrition_schemas import FoodImageAnalysis, MealLogEntry, NutritionFacts
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

load_dotenv()

# Gemini vision via LangChain
model = init_chat_model("google_genai:gemini-2.5-flash")
llm   = model.with_structured_output(FoodImageAnalysis)


def _load_image_as_base64(image_path: str) -> tuple[str, str]:
    """
    Load image from path and return (base64_string, mime_type).
    Raises FileNotFoundError if path doesn't exist.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    suffix = path.suffix.lower()
    mime_map = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(suffix, "image/jpeg")

    with open(path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    return b64, mime_type


IMAGE_SYSTEM_PROMPT = """
You are an expert food nutritionist with computer vision capabilities.

Analyse the food image and return a structured FoodImageAnalysis.

For each food item you can see:
- name: specific food name (e.g. "grilled chicken breast", not just "chicken")
- estimated_amount: your best estimate of portion size
- confidence: high / medium / low

Then estimate the TOTAL nutrition for everything visible in the image:
- calories (kcal)
- protein_g, carbs_g, fat_g
- fiber_g if you can estimate it
- sodium_mg if relevant

meal_type_guess: breakfast / lunch / dinner / snack (based on the food)
analysis_notes: any caveats (e.g. "sauce not visible, calories may be higher")
confidence_overall: high / medium / low (based on image clarity and portion visibility)

Be realistic with portion sizes. When in doubt, estimate conservatively.
"""


def image_agent_node(state: NutritionState) -> dict:
    print("\n📷 Analysing food image...")

    image_path = state.image_path
    if not image_path:
        print("   ⚠️ No image path provided in state.")
        return {"pipeline_error": "ImageAgent: no image_path in state."}

    try:
        b64_image, mime_type = _load_image_as_base64(image_path)
    except FileNotFoundError as e:
        print(f"   ❌ {e}")
        return {"pipeline_error": str(e)}

    print(f"   Loaded image: {image_path} ({mime_type})")

    # ── Build multimodal message ──────────────────────────────────────────────
    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{b64_image}"
                },
            },
            {
                "type": "text",
                "text": IMAGE_SYSTEM_PROMPT,
            },
        ]
    )

    analysis: FoodImageAnalysis = llm.invoke([message])

    # ── Print identified items ────────────────────────────────────────────────
    print(f"✅ Identified {len(analysis.identified_items)} food item(s):")
    for item in analysis.identified_items:
        print(f"   [{item.confidence}] {item.name} — {item.estimated_amount}")

    n = analysis.estimated_nutrition
    print(f"   Estimated nutrition: {n.calories} kcal | "
          f"P:{n.protein_g:.0f}g C:{n.carbs_g:.0f}g F:{n.fat_g:.0f}g")
    if analysis.analysis_notes:
        print(f"   Notes: {analysis.analysis_notes}")

    # ── Package as MealLogEntry ready for logging ─────────────────────────────
    dish_summary = ", ".join(item.name for item in analysis.identified_items[:3])
    pending_entry = MealLogEntry(
        log_date=date.today().isoformat(),
        meal_slot=analysis.meal_type_guess or "snack",
        dish_name=dish_summary,
        planned=False,                    # image log = unplanned by definition
        calories=n.calories,
        protein_g=n.protein_g,
        carbs_g=n.carbs_g,
        fat_g=n.fat_g,
        source="image",
    )

    return {
        "image_analysis":   analysis,
        "pending_log_entry": pending_entry,
    }


def confirm_and_log_image(state: NutritionState) -> dict:
    """
    Separate confirmation step — called after image_agent_node.
    Asks user to confirm before committing to the progress log.
    """
    from memory.progress_store import log_meal

    entry = state.pending_log_entry
    if not entry:
        return {}

    n = state.image_analysis.estimated_nutrition
    print(f"\n📋 Ready to log: {entry.dish_name}")
    print(f"   {entry.calories} kcal | P:{n.protein_g:.0f}g C:{n.carbs_g:.0f}g F:{n.fat_g:.0f}g")
    print(f"   Meal slot: {entry.meal_slot} | Date: {entry.log_date}")

    confirm = input("\nLog this meal? (y/n): ").strip().lower()
    if confirm == "y":
        user_id = state.customer_id or state.name or "default_user"
        log_meal(user_id, entry)
        print("   ✅ Meal logged successfully.")
    else:
        print("   ⏭️  Logging skipped.")

    return {}