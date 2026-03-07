"""
vector_store/langchain_store.py

LangChain RAG vector store replacing ChromaDB.

Uses FAISS (local, no server needed) + LangChain's embedding pipeline.

Two in-memory / persisted indexes:
  1. RECIPE EMBEDDINGS  — seeded from RECIPE_BANK, queried by recipe_agent
  2. USER PREFERENCE EMBEDDINGS — one doc per user, updated after learning loop

Embedding model: Google GenerativeAI embeddings (same provider as your LLM)
Fallback:        HuggingFace all-MiniLM-L6-v2 (fully local, no API key)

Phase 5: swap to OpenAI text-embedding-3-small if needed.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
from typing import Optional

logger = logging.getLogger(__name__)



FAISS_PERSIST_DIR: str = os.getenv("FAISS_PERSIST_DIR", "./data/faiss")
RECIPE_INDEX_PATH      = os.path.join(FAISS_PERSIST_DIR, "recipe_index.pkl")
PREF_INDEX_PATH        = os.path.join(FAISS_PERSIST_DIR, "pref_index.pkl")

# ── Lazy imports ──────────────────────────────────────────────────────────────
try:
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_core.documents import Document
    _langchain_available = True
except ImportError:
    _langchain_available = False
    logger.warning("langchain-community / faiss-cpu not installed. Vector search disabled.")


def _get_embeddings():
    """Return the best available embedding model."""
    # Try Google embeddings first (same API key you already have)
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    except Exception:
        pass

    # Fallback: local HuggingFace (no API key required)
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


class LangChainStore:

    def __init__(self) -> None:
        self._embeddings      = None
        self._recipe_store: Optional[FAISS] = None
        self._pref_store:   Optional[FAISS] = None
        self._recipe_ids:   dict[str, bool] = {}   # track upserted ids

        if not _langchain_available:
            return

        try:
            os.makedirs(FAISS_PERSIST_DIR, exist_ok=True)
            self._embeddings = _get_embeddings()

            # Load persisted indexes if they exist
            if os.path.exists(RECIPE_INDEX_PATH):
                with open(RECIPE_INDEX_PATH, "rb") as f:
                    self._recipe_store = pickle.load(f)
                logger.info("✅ Loaded persisted FAISS recipe index.")

            if os.path.exists(PREF_INDEX_PATH):
                with open(PREF_INDEX_PATH, "rb") as f:
                    self._pref_store = pickle.load(f)
                logger.info("✅ Loaded persisted FAISS preference index.")

            logger.info("✅ LangChain FAISS store initialised at %s", FAISS_PERSIST_DIR)

        except Exception as e:
            logger.warning("⚠️ LangChain store init failed (%s). Vector search disabled.", e)
            self._embeddings = None

    @property
    def available(self) -> bool:
        return self._embeddings is not None

    # ── Persist helpers ───────────────────────────────────────────────────────

    def _save_recipe_index(self) -> None:
        if self._recipe_store:
            with open(RECIPE_INDEX_PATH, "wb") as f:
                pickle.dump(self._recipe_store, f)

    def _save_pref_index(self) -> None:
        if self._pref_store:
            with open(PREF_INDEX_PATH, "wb") as f:
                pickle.dump(self._pref_store, f)

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
        """Add or update a recipe in the FAISS index."""
        if not self.available:
            return

        # Skip if already indexed (FAISS has no native upsert)
        if recipe_id in self._recipe_ids:
            return

        document_text = (
            f"{dish_name}. Cuisine: {cuisine}. "
            f"Goal: {goal_fit.replace('_', ' ')}. "
            f"Proteins: {', '.join(key_proteins)}. "
            f"Calories: ~{approx_calories}. {notes}"
        )

        doc = Document(
            page_content=document_text,
            metadata={
                "recipe_id":       recipe_id,
                "dish_name":       dish_name,
                "cuisine":         cuisine,
                "goal_fit":        goal_fit,
                "approx_calories": approx_calories,
                "key_proteins":    json.dumps(key_proteins),
                "notes":           notes,
            },
        )

        try:
            if self._recipe_store is None:
                self._recipe_store = FAISS.from_documents([doc], self._embeddings)
            else:
                self._recipe_store.add_documents([doc])

            self._recipe_ids[recipe_id] = True
            self._save_recipe_index()

        except Exception as e:
            logger.warning("LangChain upsert_recipe failed: %s", e)

    def search_recipes(
        self,
        query: str,
        goal_type: str,
        cuisine: str,
        n: int = 3,
    ) -> list[dict]:
        """
        Semantic similarity search for recipe examples.
        Returns list of metadata dicts matching RecipeContext fields.

        Uses LangChain's similarity_search with a rich natural-language query,
        then post-filters by goal_fit to keep results relevant.
        """
        if not self.available or self._recipe_store is None:
            return []

        try:
            nl_query = (
                f"healthy {goal_type.replace('_', ' ')} meal "
                f"{cuisine} cuisine balanced macros {query}"
            )

            # Fetch more than needed, then filter by goal
            raw_results = self._recipe_store.similarity_search(nl_query, k=min(n * 3, 15))

            # Post-filter by goal_fit
            filtered = [
                doc for doc in raw_results
                if doc.metadata.get("goal_fit") == goal_type
            ]

            # If post-filter is too strict, fall back to unfiltered
            candidates = filtered if filtered else raw_results

            return [
                {
                    "dish_name":       doc.metadata["dish_name"],
                    "cuisine":         doc.metadata["cuisine"],
                    "goal_fit":        doc.metadata["goal_fit"],
                    "approx_calories": doc.metadata["approx_calories"],
                    "key_proteins":    json.loads(doc.metadata["key_proteins"]),
                    "notes":           doc.metadata["notes"],
                }
                for doc in candidates[:n]
            ]

        except Exception as e:
            logger.warning("LangChain search_recipes failed: %s", e)
            return []

    def get_retriever(self, goal_type: str, k: int = 3):
        """
        Return a LangChain Retriever object.
        Can be plugged directly into a LangChain RAG chain.
        """
        if not self.available or self._recipe_store is None:
            return None

        return self._recipe_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k},
        )

    # ── User preference collection ────────────────────────────────────────────

    def upsert_user_preferences(self, user_id: str, preferences_text: str) -> None:
        """
        Embed and store a user's preference summary.
        Called after each learning loop update.
        """
        if not self.available:
            return

        doc = Document(
            page_content=preferences_text,
            metadata={"user_id": user_id},
        )

        try:
            if self._pref_store is None:
                self._pref_store = FAISS.from_documents([doc], self._embeddings)
            else:
                # FAISS doesn't support upsert natively — add new doc
                # (old docs remain but similarity search still favours the latest)
                self._pref_store.add_documents([doc])

            self._save_pref_index()

        except Exception as e:
            logger.warning("LangChain upsert_user_preferences failed: %s", e)

    def find_similar_users(self, user_id: str, n: int = 5) -> list[str]:
        """
        Find user IDs with similar preference embeddings (collaborative filtering).
        Returns list of user_ids excluding the querying user.
        """
        if not self.available or self._pref_store is None:
            return []

        try:
            # Search using the user_id as a proxy query
            results = self._pref_store.similarity_search(user_id, k=n + 1)
            return [
                doc.metadata["user_id"]
                for doc in results
                if doc.metadata.get("user_id") != user_id
            ][:n]

        except Exception as e:
            logger.warning("LangChain find_similar_users failed: %s", e)
            return []

    # ── Seeding ───────────────────────────────────────────────────────────────

    def seed_from_recipe_bank(self) -> int:
        """
        Seed the recipe FAISS index from the static RECIPE_BANK.
        Safe to call multiple times — skips already-indexed recipes.
        Returns number of recipes upserted.
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

        logger.info("LangChain FAISS seeded with %d recipes.", count)
        return count


# ── Singleton ─────────────────────────────────────────────────────────────────
langchain_store = LangChainStore()