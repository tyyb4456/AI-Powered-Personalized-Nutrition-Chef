"""
api/routers/feedback.py

Feedback endpoints:
  POST   /feedback/              — submit a recipe rating + comment
  GET    /feedback/              — list all feedback by the current user
  DELETE /feedback/{feedback_id} — delete a specific feedback entry
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from schemas.tracking_schemas import (
    SubmitFeedbackRequest, FeedbackResponse, FeedbackListResponse,
)
from services.tracking_service import (
    submit_feedback, list_feedback, delete_feedback,
)
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])

from typing import Optional


# ── POST /feedback/ ───────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback for a recipe",
    description="""
Rate a recipe and optionally leave a comment.

This is the REST equivalent of the CLI's `interrupt()`-based feedback collection.  
The `recipe_id` is returned in the response of `POST /recipes/generate`.

Feedback is stored in the `user_feedback` table and later consumed by the  
**learning loop agent** to improve future recipe recommendations.
""",
)
def submit_feedback_endpoint(
    payload: SubmitFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return submit_feedback(user=current_user, db=db, payload=payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── GET /feedback/ ────────────────────────────────────────────────────────────

@router.get("/", response_model=FeedbackListResponse)
def list_my_feedback(
    page:      int          = Query(default=1, ge=1),
    limit:     int          = Query(default=20, ge=1, le=100),
    recipe_id: Optional[str] = Query(default=None),   # ← add this
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_feedback(user_id=current_user.id, db=db, page=page, limit=limit, recipe_id=recipe_id)


# ── DELETE /feedback/{feedback_id} ────────────────────────────────────────────

@router.delete(
    "/{feedback_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a feedback entry",
)
def delete_feedback_endpoint(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete feedback by ID. Users can only delete their own feedback.
    Returns 204 No Content on success, 404 if not found.
    """
    deleted = delete_feedback(feedback_id=feedback_id, user_id=current_user.id, db=db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback '{feedback_id}' not found.",
        )