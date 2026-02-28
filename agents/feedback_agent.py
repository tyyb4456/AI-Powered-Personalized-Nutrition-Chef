"""
agents/feedback_agent.py — Phase 4

Phase 4 upgrade:
- Persists feedback to user_feedback table via UserRepository
- Links feedback to user_id + recipe_id from state
- Still collects interactively; Phase 5 will move this to API endpoint
"""

from __future__ import annotations

import logging

from state import NutritionState

logger = logging.getLogger(__name__)


def feedback_agent_node(state: NutritionState) -> dict:
    print("\n🧪 Collecting feedback on the meal...")

    while True:
        try:
            rating = int(input("⭐ Rate the recipe (1–5): ").strip())
            if 1 <= rating <= 5:
                break
            print("   ⚠️ Please enter a number between 1 and 5.")
        except ValueError:
            print("   ⚠️ Invalid input. Enter a number.")

    comment = input("📝 Any comments or suggestions? ").strip() or None

    # ── Persist to DB ─────────────────────────────────────────────────────────
    user_id   = state.customer_id or state.name or "anonymous"
    recipe_id = getattr(state, "current_recipe_id", None)

    if recipe_id:
        try:
            from db.database import get_db
            from db.repositories import UserRepository
            with get_db() as db:
                UserRepository(db).save_feedback(
                    user_id=user_id,
                    recipe_id=recipe_id,
                    rating=rating,
                    comment=comment,
                )
            print(f"   💾 Feedback saved to DB.")
        except Exception as e:
            logger.warning("Could not save feedback to DB (%s).", e)
    else:
        logger.info("No recipe_id in state — feedback not persisted.")

    return {
        "feedback_rating":    rating,
        "feedback_comment":   comment,
        "feedback_collected": True,
    }