"""
vector_store/chroma_store.py

ChromaDB vector store for two collections:

1. RECIPE EMBEDDINGS
   - Populated from the static recipe bank (and future recipe DB)
   - Queried by recipe_agent to get relevant examples before generation
   - Replaces the keyword-matching in recipe_context_store.py

2. USER PREFERENCE EMBEDDINGS
   - One document per user, updated after each learning loop
   - Queried to find similar users for cold-start recommendations
   - Powers "users like you also enjoyed..." suggestions (Phase 5)

Uses ChromaDB's default embedding function (sentence-transformers all-MiniLM-L6-v2)
which runs locally — no extra API key needed.

Phase 5: swap to OpenAI text-embedding-3-small or Google's embedding API
for higher-quality semantic search.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── Lazy import ───────────────────────────────────────────────────────────────
try:
    import chromadb
    from chromadb.config import Settings
    _chroma_available = True
except ImportError:
    _chroma_available = False
    logger.warning("chromadb not installed. Vector search disabled — falling back to keyword matching.")


CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

# ── Collection names ──────────────────────────────────────────────────────────
RECIPE_COLLECTION      = "recipe_examples"
PREFERENCE_COLLECTION  = "user_preferences"


class ChromaStore:

    def __init__(self) -> None:
        self._client = None
        self._recipe_col = None
        self._pref_col   = None

        if not _chroma_available:
            return

        try:
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            self._recipe_col = self._client.get_or_create_collection(RECIPE_COLLECTION)
            self._pref_col   = self._client.get_or_create_collection(PREFERENCE_COLLECTION)
            logger.info("✅ ChromaDB initialised at %s", CHROMA_PERSIST_DIR)
        except Exception as e:
            logger.warning("⚠️ ChromaDB init failed (%s). Vector search disabled.", e)
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    # ── Recipe collection ─────────────────────────────────────────────────────

    def upsert_recipe(
        self,
        recipe_id: str,
        dish_name: str,
        cuisine: str,
        goal_fit: str,
        key_proteins: list[str],
        approx_calories: int,
        notes: str,
    ) -> None:
        """
        Add or update a recipe example in the vector store.
        The document string is what gets embedded — design it to be semantically rich.
        """
        if not self.available:
            return

        document = (
            f"{dish_name}. Cuisine: {cuisine}. "
            f"Goal: {goal_fit.replace('_', ' ')}. "
            f"Proteins: {', '.join(key_proteins)}. "
            f"Calories: ~{approx_calories}. {notes}"
        )
        metadata = {
            "dish_name":       dish_name,
            "cuisine":         cuisine,
            "goal_fit":        goal_fit,
            "approx_calories": approx_calories,
            "key_proteins":    json.dumps(key_proteins),
            "notes":           notes,
        }

        try:
            self._recipe_col.upsert(
                ids=[recipe_id],
                documents=[document],
                metadatas=[metadata],
            )
        except Exception as e:
            logger.warning("ChromaDB upsert_recipe failed: %s", e)

    def search_recipes(
        self,
        query: str,
        goal_type: str,
        cuisine: str,
        n: int = 3,
    ) -> list[dict]:
        """
        Semantic search for relevant recipe examples.
        Returns a list of metadata dicts (matching RecipeContext fields).

        Falls back to empty list if unavailable.
        """
        if not self.available:
            return []

        try:
            # Build a rich natural language query
            nl_query = (
                f"{goal_type.replace('_', ' ')} meal, {cuisine} cuisine. "
                f"Healthy, balanced macros. {query}"
            )

            results = self._recipe_col.query(
                query_texts=[nl_query],
                n_results=min(n, self._recipe_col.count()),
                where={"goal_fit": goal_type},   # pre-filter by goal
            )

            if not results["metadatas"] or not results["metadatas"][0]:
                return []

            return [
                {
                    "dish_name":       m["dish_name"],
                    "cuisine":         m["cuisine"],
                    "goal_fit":        m["goal_fit"],
                    "approx_calories": m["approx_calories"],
                    "key_proteins":    json.loads(m["key_proteins"]),
                    "notes":           m["notes"],
                }
                for m in results["metadatas"][0]
            ]
        except Exception as e:
            logger.warning("ChromaDB search_recipes failed: %s", e)
            return []

    # ── User preference collection ────────────────────────────────────────────

    def upsert_user_preferences(self, user_id: str, preferences_text: str) -> None:
        """
        Embed and store a text summary of a user's preferences.
        Called after each learning loop update.
        """
        if not self.available:
            return
        try:
            self._pref_col.upsert(
                ids=[user_id],
                documents=[preferences_text],
                metadatas=[{"user_id": user_id}],
            )
        except Exception as e:
            logger.warning("ChromaDB upsert_user_preferences failed: %s", e)

    def find_similar_users(self, user_id: str, n: int = 5) -> list[str]:
        """
        Find user IDs with similar preference embeddings.
        Used for collaborative filtering recommendations.
        Returns list of similar user_ids (excluding the querying user).
        """
        if not self.available:
            return []
        try:
            # First get this user's preference text
            result = self._pref_col.get(ids=[user_id])
            if not result["documents"]:
                return []

            user_doc = result["documents"][0]
            similar  = self._pref_col.query(
                query_texts=[user_doc],
                n_results=min(n + 1, self._pref_col.count()),
            )

            ids = similar["ids"][0] if similar["ids"] else []
            return [uid for uid in ids if uid != user_id][:n]

        except Exception as e:
            logger.warning("ChromaDB find_similar_users failed: %s", e)
            return []

    # ── Seeding ───────────────────────────────────────────────────────────────

    def seed_from_recipe_bank(self) -> int:
        """
        Seed the recipe collection from the static recipe bank.
        Returns number of recipes upserted.
        Safe to call multiple times (upsert = no duplicates).
        """
        if not self.available:
            return 0

        from memory.recipe_context_store import RECIPE_BANK

        count = 0
        for i, recipe in enumerate(RECIPE_BANK):
            recipe_id = f"static_{i:04d}"
            self.upsert_recipe(
                recipe_id=recipe_id,
                dish_name=recipe.dish_name,
                cuisine=recipe.cuisine,
                goal_fit=recipe.goal_fit,
                key_proteins=recipe.key_proteins,
                approx_calories=recipe.approx_calories,
                notes=recipe.notes,
            )
            count += 1

        logger.info("ChromaDB seeded with %d recipes.", count)
        return count


# ── Singleton ─────────────────────────────────────────────────────────────────
chroma_store = ChromaStore()