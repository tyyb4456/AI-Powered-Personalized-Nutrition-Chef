"""
api/routers/images.py

Food image analysis endpoints:

  POST /images/analyse          — analyse food image (base64 JSON body)
  POST /images/upload           — analyse food image (multipart file upload)

Both return an ImageAnalysisResponse with:
  - identified food items + confidence
  - estimated nutrition (calories, protein, carbs, fat, fiber)
  - meal_type_guess (breakfast/lunch/dinner/snack)
  - analysis_notes (caveats like "sauce not visible")
  - optional: log_id if auto_log=True

The two endpoints exist to support different client types:
  - Mobile / SPA apps tend to encode images as base64 and send JSON
  - Traditional web forms use multipart file upload
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from schemas.image_schemas import AnalyseImageRequest, ImageAnalysisResponse
from services.image_service import analyse_image_base64, analyse_image_upload
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["Food Image Analysis"])

# Accepted MIME types for upload endpoint
ACCEPTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES        = 10 * 1024 * 1024   # 10 MB


# ── POST /images/analyse  (base64 JSON) ──────────────────────────────────────

@router.post(
    "/analyse",
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse a food image (base64)",
    description="""
Send a food photo as a **base64-encoded string** and get back:

- All identified food items with confidence levels
- Full estimated nutrition (calories, protein, carbs, fat, fiber)
- Meal type guess (breakfast / lunch / dinner / snack)
- Analysis caveats (e.g. "sauce not visible, calories may be higher")

**`auto_log`** — set to `true` to immediately log the identified meal to  
your meal log history (equivalent to `POST /meal-logs/` after analysis).

**`meal_slot`** — override the detected meal type if the model guessed wrong.

⏱️ Typical response time: 3–8 seconds (Gemini vision call).

**Accepted formats:** JPEG, PNG, WEBP  
**Max size:** 10 MB
""",
)
async def analyse_base64(
    payload: AnalyseImageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await analyse_image_base64(
            user=current_user, db=db, request=payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Image analysis failed for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image analysis failed: {str(e)}",
        )


# ── POST /images/upload  (multipart) ─────────────────────────────────────────

@router.post(
    "/upload",
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse a food image (file upload)",
    description="""
Upload a food photo as a **multipart file** and get nutritional analysis back.

Same response as `/images/analyse` — two endpoints for two client patterns.

**Form fields:**
- `file` — the image file (required)
- `auto_log` — `true` / `false` (default: `false`)
- `log_date` — ISO date string e.g. `2026-03-05` (default: today)
- `meal_slot` — override slot: `breakfast` / `lunch` / `dinner` / `snack`

**Accepted formats:** JPEG, PNG, WEBP  
**Max size:** 10 MB

**Example (curl):**
```bash
curl -X POST http://localhost:8000/images/upload \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -F "file=@/path/to/food.jpg" \\
  -F "auto_log=true" \\
  -F "meal_slot=lunch"
```
""",
)
async def upload_image(
    file:      UploadFile              = File(..., description="Food image file (JPEG/PNG/WEBP)"),
    auto_log:  bool                    = Form(default=False),
    log_date:  Optional[str]           = Form(default=None),
    meal_slot: Optional[str]           = Form(default=None),
    current_user: User  = Depends(get_current_user),
    db: Session         = Depends(get_db),
):
    # Validate content type
    content_type = file.content_type or "image/jpeg"
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{content_type}'. "
                f"Accepted: {', '.join(sorted(ACCEPTED_CONTENT_TYPES))}"
            ),
        )

    # Read bytes
    raw_bytes = await file.read()
    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is 10 MB.",
        )

    try:
        return await analyse_image_upload(
            user      = current_user,
            db        = db,
            raw_bytes = raw_bytes,
            mime_type = content_type,
            auto_log  = auto_log,
            log_date  = log_date,
            meal_slot = meal_slot,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Image upload analysis failed for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image analysis failed: {str(e)}",
        )