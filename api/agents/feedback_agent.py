"""
agents/feedback_agent.py — Phase 4 (interrupt fix)

Uses LangGraph's interrupt() for human-in-the-loop input instead of
plain input() calls.

How interrupt() works:
  1. The node calls interrupt("prompt string") — this pauses the graph
     and returns the prompt string to the caller via GraphInterrupt.
  2. main.py catches the interrupt, shows the prompt, reads user input.
  3. main.py calls graph_builder.resume_for_user(user_id, answer).
  4. The graph resumes from the SAME node, and interrupt() now returns
     the user's answer instead of raising.

This means the node runs TWICE per interrupt():
  - First pass:  interrupt() raises GraphInterrupt → node execution stops
  - Second pass: interrupt() returns the user's answer → node continues

We use two interrupt() calls — one for rating, one for comment — so the
node runs a total of three times per feedback collection:
  pass 1: rating interrupt raised
  pass 2: rating returned, comment interrupt raised
  pass 3: comment returned, feedback saved to DB, node returns state

The `_collected` flag in state prevents double-saving on re-entry.
"""

from __future__ import annotations

import logging

from langgraph.types import interrupt
from state import NutritionState

logger = logging.getLogger(__name__)


def feedback_agent_node(state: NutritionState) -> dict:
    # Already collected in a previous pass — skip re-collection
    if state.feedback_collected:
        return {}

    print("\n🧪 Collecting feedback on the meal...")

    # ── Pass 1 / 2: collect rating via interrupt ──────────────────────────────
    while True:
        raw_rating = interrupt("⭐ Rate the recipe (1–5):")
        try:
            rating = int(str(raw_rating).strip())
            if 1 <= rating <= 5:
                break
            print("   ⚠️ Please enter a number between 1 and 5.")
        except (ValueError, TypeError):
            print("   ⚠️ Invalid input. Enter a number between 1 and 5.")

    # ── Pass 2 / 3: collect comment via interrupt ─────────────────────────────
    raw_comment = interrupt("📝 Any comments or suggestions? (press Enter to skip):")
    comment = str(raw_comment).strip() or None

    # ── Persist to DB ─────────────────────────────────────────────────────────
    user_id   = state.customer_id or state.name or "anonymous"
    recipe_id = state.current_recipe_id

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
            print("   💾 Feedback saved to DB.")
        except Exception as e:
            logger.warning("Could not save feedback to DB (%s).", e)
    else:
        logger.info("No recipe_id in state — feedback not linked to a recipe row.")

    return {
        "feedback_rating":    rating,
        "feedback_comment":   comment,
        "feedback_collected": True,
    }