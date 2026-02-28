"""
cache/redis_client.py

Redis wrapper for three use cases:

1. SESSION CACHE
   key: session:{user_id}
   value: JSON-serialised NutritionState
   TTL: 1 hour
   Use: resume an interrupted pipeline without re-running profile_agent

2. RECIPE CACHE
   key: recipe_cache:{hash_of_profile_and_goal}
   value: JSON-serialised RecipeOutput
   TTL: 24 hours
   Use: if the same user requests the same recipe twice within 24h,
        skip LLM call and serve cached version instantly

3. RATE LIMITING
   key: rate_limit:{user_id}
   value: integer counter (incremented per LLM call)
   TTL: 1 hour (rolling)
   Use: prevent a single user from burning unlimited API credits

All methods fail gracefully — if Redis is unavailable, the system
continues without caching (degraded but functional).
"""

from __future__ import annotations

import hashlib
import json
import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ── Lazy import so the app starts even if redis-py is not installed ───────────
try:
    import redis
    _redis_available = True
except ImportError:
    _redis_available = False
    logger.warning("redis-py not installed. Caching disabled.")


REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ── TTLs ──────────────────────────────────────────────────────────────────────
SESSION_TTL_SECONDS     = 60 * 60       # 1 hour
RECIPE_CACHE_TTL_SECONDS = 60 * 60 * 24 # 24 hours
RATE_LIMIT_TTL_SECONDS  = 60 * 60       # 1 hour (rolling window)
RATE_LIMIT_MAX_CALLS    = int(os.getenv("RATE_LIMIT_MAX_CALLS", "20"))


class RedisClient:
    """
    Thin wrapper around redis.Redis.
    All methods return None / False on failure instead of raising.
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        if _redis_available:
            try:
                self._client = redis.from_url(REDIS_URL, decode_responses=True)
                self._client.ping()
                logger.info("✅ Redis connected: %s", REDIS_URL)
            except Exception as e:
                logger.warning("⚠️ Redis unavailable (%s). Caching disabled.", e)
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    # ── Session ───────────────────────────────────────────────────────────────

    def save_session(self, user_id: str, state_dict: dict) -> bool:
        """Serialise and cache the full agent state for a user."""
        if not self.available:
            return False
        try:
            key = f"session:{user_id}"
            self._client.setex(key, SESSION_TTL_SECONDS, json.dumps(state_dict, default=str))
            return True
        except Exception as e:
            logger.warning("Redis save_session failed: %s", e)
            return False

    def load_session(self, user_id: str) -> Optional[dict]:
        """Return cached state dict, or None if not found / expired."""
        if not self.available:
            return None
        try:
            key  = f"session:{user_id}"
            data = self._client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Redis load_session failed: %s", e)
            return None

    def delete_session(self, user_id: str) -> None:
        if not self.available:
            return
        try:
            self._client.delete(f"session:{user_id}")
        except Exception as e:
            logger.warning("Redis delete_session failed: %s", e)

    # ── Recipe cache ──────────────────────────────────────────────────────────

    @staticmethod
    def _recipe_cache_key(user_id: str, goal_type: str, calorie_target: int,
                          cuisine: str, allergies: list[str]) -> str:
        """Deterministic key based on the inputs that drive recipe generation."""
        raw = f"{user_id}|{goal_type}|{calorie_target}|{cuisine}|{sorted(allergies)}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"recipe_cache:{digest}"

    def cache_recipe(self, recipe_dict: dict, user_id: str, goal_type: str,
                     calorie_target: int, cuisine: str, allergies: list[str]) -> bool:
        if not self.available:
            return False
        try:
            key = self._recipe_cache_key(user_id, goal_type, calorie_target, cuisine, allergies)
            self._client.setex(key, RECIPE_CACHE_TTL_SECONDS, json.dumps(recipe_dict, default=str))
            logger.info("Recipe cached: %s", key)
            return True
        except Exception as e:
            logger.warning("Redis cache_recipe failed: %s", e)
            return False

    def get_cached_recipe(self, user_id: str, goal_type: str, calorie_target: int,
                          cuisine: str, allergies: list[str]) -> Optional[dict]:
        if not self.available:
            return None
        try:
            key  = self._recipe_cache_key(user_id, goal_type, calorie_target, cuisine, allergies)
            data = self._client.get(key)
            if data:
                logger.info("Cache HIT: %s", key)
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("Redis get_cached_recipe failed: %s", e)
            return None

    # ── Rate limiting ─────────────────────────────────────────────────────────

    def check_rate_limit(self, user_id: str) -> tuple[bool, int]:
        """
        Returns (is_allowed: bool, current_count: int).
        Increments counter on each call.
        """
        if not self.available:
            return True, 0   # allow if Redis is down

        try:
            key   = f"rate_limit:{user_id}"
            count = self._client.incr(key)
            if count == 1:
                # First call in this window — set TTL
                self._client.expire(key, RATE_LIMIT_TTL_SECONDS)

            allowed = count <= RATE_LIMIT_MAX_CALLS
            if not allowed:
                logger.warning("Rate limit exceeded for user %s (%d calls)", user_id, count)
            return allowed, count
        except Exception as e:
            logger.warning("Redis check_rate_limit failed: %s", e)
            return True, 0   # allow on error

    def get_rate_limit_status(self, user_id: str) -> dict:
        if not self.available:
            return {"calls_used": 0, "calls_remaining": RATE_LIMIT_MAX_CALLS, "redis_available": False}
        try:
            count = int(self._client.get(f"rate_limit:{user_id}") or 0)
            return {
                "calls_used":      count,
                "calls_remaining": max(0, RATE_LIMIT_MAX_CALLS - count),
                "redis_available": True,
            }
        except Exception as e:
            return {"calls_used": 0, "calls_remaining": RATE_LIMIT_MAX_CALLS, "error": str(e)}


# ── Singleton ─────────────────────────────────────────────────────────────────
redis_client = RedisClient()