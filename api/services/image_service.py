"""
api/services/image_service.py

Business logic for food image analysis.

Two entry points:
  analyse_image_base64()   — accepts base64 string + mime_type from JSON body
  analyse_image_upload()   — accepts raw bytes from multipart file upload

Both call _run_image_pipeline() in a ThreadPoolExecutor (Gemini vision is blocking).

The pipeline:
  1. Build a NutritionState with image_base64 set instead of image_path
  2. Call a modified image_agent that accepts base64 directly (no file I/O)
  3. Optionally auto-log the result to meal_logs table

Key difference from CLI:
  CLI image_agent reads from a file path on disk.
  API image_agent receives base64 directly — avoids temp file creation.
"""

from __future__ import annotations

import base64
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from db.models import User
from db.repositories import ProgressRepository
from schemas.nutrition_schemas import FoodImageAnalysis, MealLogEntry, NutritionFacts
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from schemas.image_schemas import (
    AnalyseImageRequest,
    ImageAnalysisResponse,
    IdentifiedFoodItemOut,
    NutritionEstimateOut,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)

# ── Gemini vision model ───────────────────────────────────────────────────────
model = init_chat_model("google_genai:gemini-2.5-flash")
llm   = model.with_structured_output(FoodImageAnalysis)

IMAGE_SYSTEM_PROMPT = """
You are an expert food nutritionist with computer vision capabilities.

Analyse the food image and return a structured FoodImageAnalysis.

For each food item you can see:
- name: specific food name (e.g. "grilled chicken breast", not just "chicken")
- estimated_amount: your best estimate of portion size (e.g. "150g", "1 cup")
- confidence: high / medium / low

Then estimate the TOTAL nutrition for everything visible in the image:
- calories (kcal)
- protein_g, carbs_g, fat_g
- fiber_g if estimable
- sodium_mg if relevant

meal_type_guess: breakfast / lunch / dinner / snack (infer from the food)
analysis_notes: any important caveats (e.g. "sauce not visible, calories may be higher")
confidence_overall: high / medium / low (based on image clarity and portion visibility)

Be realistic with portion sizes. When in doubt, estimate conservatively.
Do not hallucinate food items you cannot see clearly.
"""

VALID_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
VALID_SLOTS      = {"breakfast", "lunch", "dinner", "snack"}


# ═══════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════

def _validate_mime(mime_type: str) -> None:
    if mime_type not in VALID_MIME_TYPES:
        raise ValueError(
            f"Unsupported image type '{mime_type}'. "
            f"Accepted: {', '.join(sorted(VALID_MIME_TYPES))}"
        )


def _validate_base64(b64: str) -> bytes:
    """Decode and validate base64 string. Strips data-URL prefix if present."""
    # Strip "data:image/jpeg;base64," prefix if client sent a data URL
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    try:
        return base64.b64decode(b64)
    except Exception:
        raise ValueError("Invalid base64 image data.")


def _validate_image_size(raw_bytes: bytes, max_mb: float = 10.0) -> None:
    size_mb = len(raw_bytes) / (1024 * 1024)
    if size_mb > max_mb:
        raise ValueError(f"Image too large ({size_mb:.1f} MB). Maximum allowed: {max_mb} MB.")


# ═══════════════════════════════════════════════════════════════
# CORE VISION CALL (blocking — runs in thread pool)
# ═══════════════════════════════════════════════════════════════

def _call_vision_llm(b64_string: str, mime_type: str) -> FoodImageAnalysis:
    """
    Send base64 image to Gemini vision and get structured FoodImageAnalysis back.
    This is a blocking call — always run via executor.
    """
    message = HumanMessage(
        content=[
            {
                "type":      "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64_string}"},
            },
            {
                "type": "text",
                "text": IMAGE_SYSTEM_PROMPT,
            },
        ]
    )
    return llm.invoke([message])


# ═══════════════════════════════════════════════════════════════
# RESPONSE BUILDER
# ═══════════════════════════════════════════════════════════════

def _build_response(
    analysis: FoodImageAnalysis,
    log_id: Optional[str] = None,
    logged: bool = False,
) -> ImageAnalysisResponse:
    n = analysis.estimated_nutrition
    return ImageAnalysisResponse(
        identified_items=[
            IdentifiedFoodItemOut(
                name             = item.name,
                estimated_amount = item.estimated_amount,
                confidence       = item.confidence,
            )
            for item in analysis.identified_items
        ],
        estimated_nutrition = NutritionEstimateOut(
            calories  = n.calories,
            protein_g = n.protein_g,
            carbs_g   = n.carbs_g,
            fat_g     = n.fat_g,
            fiber_g   = n.fiber_g,
            sodium_mg = n.sodium_mg,
        ),
        meal_type_guess    = analysis.meal_type_guess,
        analysis_notes     = analysis.analysis_notes,
        confidence_overall = analysis.confidence_overall,
        dish_summary       = ", ".join(i.name for i in analysis.identified_items[:3]),
        log_id             = log_id,
        logged             = logged,
    )


# ═══════════════════════════════════════════════════════════════
# AUTO-LOG HELPER
# ═══════════════════════════════════════════════════════════════

def _auto_log(
    user_id: str,
    analysis: FoodImageAnalysis,
    db: Session,
    log_date: Optional[str],
    meal_slot: Optional[str],
) -> str:
    """Persist the identified meal to meal_logs. Returns log_id."""
    n = analysis.estimated_nutrition

    # Use detected slot, or override, or fall back to "snack"
    slot = meal_slot or analysis.meal_type_guess or "snack"
    if slot not in VALID_SLOTS:
        slot = "snack"

    today     = date.today().isoformat()
    entry_date = log_date or today

    # Validate date
    try:
        date.fromisoformat(entry_date)
    except ValueError:
        entry_date = today

    dish_summary = ", ".join(i.name for i in analysis.identified_items[:3])

    entry = MealLogEntry(
        log_date  = entry_date,
        meal_slot = slot,
        dish_name = dish_summary,
        planned   = False,
        calories  = n.calories,
        protein_g = n.protein_g,
        carbs_g   = n.carbs_g,
        fat_g     = n.fat_g,
        source    = "image",
    )

    repo   = ProgressRepository(db)
    log_id = repo.log_meal(user_id, entry, recipe_id=None)
    db.flush()

    logger.info(
        "Auto-logged image meal: user=%s date=%s slot=%s dish=%s (%d kcal)",
        user_id, entry_date, slot, dish_summary, n.calories,
    )
    return log_id


# ═══════════════════════════════════════════════════════════════
# PUBLIC SERVICE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def analyse_image_base64(
    user: User,
    db: Session,
    request: AnalyseImageRequest,
) -> ImageAnalysisResponse:
    """
    Analyse a base64-encoded food image.
    Optionally auto-logs the result if request.auto_log is True.
    """
    import asyncio

    # Validate
    _validate_mime(request.mime_type)
    raw_bytes = _validate_base64(request.image_base64)
    _validate_image_size(raw_bytes)

    # Re-encode validated bytes (strips any data-URL prefix)
    clean_b64 = base64.standard_b64encode(raw_bytes).decode("utf-8")

    # Run vision LLM in thread (blocking Gemini call)
    loop     = asyncio.get_event_loop()
    analysis = await loop.run_in_executor(
        _executor, _call_vision_llm, clean_b64, request.mime_type,
    )

    # Optional auto-log
    log_id = None
    logged = False
    if request.auto_log:
        log_id = _auto_log(
            user_id   = user.id,
            analysis  = analysis,
            db        = db,
            log_date  = request.log_date,
            meal_slot = request.meal_slot,
        )
        logged = True

    return _build_response(analysis, log_id=log_id, logged=logged)


async def analyse_image_upload(
    user: User,
    db: Session,
    raw_bytes: bytes,
    mime_type: str,
    auto_log: bool = False,
    log_date: Optional[str] = None,
    meal_slot: Optional[str] = None,
) -> ImageAnalysisResponse:
    """
    Analyse a food image from raw bytes (multipart file upload).
    Same logic as base64 path but bytes come directly from the upload.
    """
    import asyncio

    _validate_mime(mime_type)
    _validate_image_size(raw_bytes)

    clean_b64 = base64.standard_b64encode(raw_bytes).decode("utf-8")

    loop     = asyncio.get_event_loop()
    analysis = await loop.run_in_executor(
        _executor, _call_vision_llm, clean_b64, mime_type,
    )

    log_id = None
    logged = False
    if auto_log:
        log_id = _auto_log(
            user_id   = user.id,
            analysis  = analysis,
            db        = db,
            log_date  = log_date,
            meal_slot = meal_slot,
        )
        logged = True

    return _build_response(analysis, log_id=log_id, logged=logged)