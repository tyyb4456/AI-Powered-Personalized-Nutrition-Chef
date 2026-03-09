"""
api/routers/analytics.py

Analytics & learning endpoints:

Progress:
  POST GET /analytics/progress          — generate (LLM) or re-fetch weekly report

Learned preferences:
  GET    /analytics/preferences         — fetch current learned preferences
  PUT    /analytics/preferences         — manually update preferences
  DELETE /analytics/preferences         — reset all learned preferences

Learning loop:
  POST   /analytics/learn               — trigger learning loop on a feedback entry
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from schemas.analytics_schemas import (
    GenerateProgressReportRequest,
    ProgressReportResponse,
    LearnedPreferencesResponse,
    UpdateLearnedPreferencesRequest,
    TriggerLearningRequest,
    TriggerLearningResponse,
)
from services.analytics_service import (
    generate_progress_report,
    get_learned_preferences,
    update_learned_preferences,
    reset_learned_preferences,
    trigger_learning,
    get_saved_progress_report,
)
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics & Learning"])


# ═══════════════════════════════════════════════════════════════
# PROGRESS REPORT
# ═══════════════════════════════════════════════════════════════

# ── POST /analytics/progress — regenerates via LLM ───────────────────────────
@router.post(
    "/progress",
    response_model=ProgressReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a weekly progress report",
)
async def generate_progress_report_endpoint(
    payload: GenerateProgressReportRequest = GenerateProgressReportRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await generate_progress_report(user=current_user, db=db, request=payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.exception("Progress report failed for user %s", current_user.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Progress report generation failed: {str(e)}")


# ── GET /analytics/progress — returns cached report, no LLM call ─────────────
@router.get(
    "/progress",
    response_model=ProgressReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the last generated progress report",
)
def get_progress_report_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = get_saved_progress_report(user_id=current_user.id, db=db)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report generated yet. Call POST /analytics/progress first.",
        )
    return report

# ═══════════════════════════════════════════════════════════════
# LEARNED PREFERENCES
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/preferences",
    response_model=LearnedPreferencesResponse,
    summary="Get your learned preferences",
    description="""
Returns the preferences accumulated by the **learning loop agent** across
all your recipe feedback sessions.

These are used automatically by the recipe generator to personalise future meals:
- `liked_ingredients` / `disliked_ingredients` — ingredient-level preferences
- `preferred_textures` — e.g. crispy, tender, creamy
- `preferred_cuisines` / `avoided_cuisines` — cuisine-level preferences
- `spice_preference` — low / medium / high
- `goal_refinement` — any goal evolution detected from feedback
- `session_insights` — last 5 key insights from feedback sessions
""",
)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_learned_preferences(user_id=current_user.id, db=db)


@router.put(
    "/preferences",
    response_model=LearnedPreferencesResponse,
    summary="Manually update learned preferences",
    description="""
Manually set or override preference fields.

All fields are **optional** — only provided fields are updated.  
Omitted fields keep their current values.

Useful for onboarding flows where you want to seed initial preferences
before the user has generated any recipes.
""",
)
def update_preferences(
    payload: UpdateLearnedPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_learned_preferences(
        user_id=current_user.id, db=db, payload=payload,
    )


@router.delete(
    "/preferences",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset all learned preferences",
    description="""
Deletes all learned preferences for the authenticated user.

The learning loop will start fresh from the next feedback submission.  
This does **not** affect the user's saved profile (age, weight, etc.).
""",
)
def reset_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reset_learned_preferences(user_id=current_user.id, db=db)


# ═══════════════════════════════════════════════════════════════
# LEARNING LOOP TRIGGER
# ═══════════════════════════════════════════════════════════════

@router.post(
    "/learn",
    response_model=TriggerLearningResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger the learning loop on a feedback entry",
    description="""
Manually triggers the **learning loop agent** (Gemini 2.5 Flash) on a specific
feedback entry. The LLM reads the rating + comment and updates your learned
preferences accordingly.

**When to use:**  
The learning loop runs automatically during the CLI pipeline. In the API,
feedback is decoupled from recipe generation — call this endpoint after  
submitting feedback via `POST /feedback/` to ensure preferences are updated.

**`feedback_id`** — obtained from the response of `POST /feedback/`.

⏱️ Typical response time: 3–8 seconds.
""",
)
async def learn_from_feedback(
    payload: TriggerLearningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await trigger_learning(
            user=current_user, db=db, request=payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Learning loop failed for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Learning loop failed: {str(e)}",
        )