"""
api/schemas/image_schemas.py

Request / response models for food image analysis endpoints.

The API accepts images as:
  - base64-encoded string (easiest for mobile clients)
  - multipart file upload (traditional web upload)

Both paths produce the same response.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# REQUEST
# ═══════════════════════════════════════════════════════════════

class AnalyseImageRequest(BaseModel):
    """
    JSON body for base64 image submission.
    Used when the client encodes the image themselves.
    """
    image_base64: str  = Field(
        ...,
        description="Base64-encoded image bytes (no data-URL prefix needed)",
    )
    mime_type: str = Field(
        default="image/jpeg",
        description="MIME type of the image: image/jpeg | image/png | image/webp",
        examples=["image/jpeg"],
    )
    # Optional: immediately log the identified meal
    auto_log:   bool          = Field(
        default=False,
        description="If true, automatically log the identified meal to meal logs",
    )
    log_date:   Optional[str] = Field(
        default=None,
        description="ISO date for auto-log e.g. '2026-03-05'. Defaults to today.",
    )
    meal_slot:  Optional[str] = Field(
        default=None,
        description="Override detected meal slot: breakfast/lunch/dinner/snack",
    )


# ═══════════════════════════════════════════════════════════════
# RESPONSE BUILDING BLOCKS
# ═══════════════════════════════════════════════════════════════

class IdentifiedFoodItemOut(BaseModel):
    name:             str
    estimated_amount: str
    confidence:       str   # high / medium / low


class NutritionEstimateOut(BaseModel):
    calories:   int
    protein_g:  float
    carbs_g:    float
    fat_g:      float
    fiber_g:    Optional[float] = None
    sodium_mg:  Optional[float] = None


# ═══════════════════════════════════════════════════════════════
# MAIN RESPONSE
# ═══════════════════════════════════════════════════════════════

class ImageAnalysisResponse(BaseModel):
    identified_items:   list[IdentifiedFoodItemOut]
    estimated_nutrition: NutritionEstimateOut
    meal_type_guess:    Optional[str]   = None   # breakfast/lunch/dinner/snack
    analysis_notes:     str             = ""
    confidence_overall: str                      # high / medium / low
    dish_summary:       str                      # comma-joined item names
    # Set when auto_log=True or POST /images/analyse-and-log is used
    log_id:             Optional[str]   = None
    logged:             bool            = False