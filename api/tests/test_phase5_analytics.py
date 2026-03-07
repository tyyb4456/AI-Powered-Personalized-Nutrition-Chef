"""
tests/test_phase5_analytics.py

Tests for Phase 5 — progress reports and learned preferences.

- Progress report: LLM mocked, runs fast
- Learned preferences: pure DB, no mocks needed
- Learning trigger: LLM mocked, runs fast

Run with:
  pytest tests/test_phase5_analytics.py -v
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
from app import create_app
from dependencies import get_db
from schemas.analytics_schemas import (
    ProgressReportResponse,
    LearnedPreferencesResponse,
    TriggerLearningResponse,
)

# ── SQLite test DB ────────────────────────────────────────────────────────────
SQLITE_URL = "sqlite:///./test_analytics.db"
engine_test = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine_test, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client():
    app = create_app()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    client.post("/auth/register", json={"name": "Analytics User", "password": "pass1234"})
    resp = client.post("/auth/login", json={"name": "Analytics User", "password": "pass1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def auth_headers_with_profile(client, auth_headers):
    client.put("/users/me", json={
        "age": 30, "gender": "male", "weight_kg": 80.0,
        "height_cm": 178.0, "activity_level": "moderate",
        "fitness_goal": "fat_loss",
    }, headers=auth_headers)
    return auth_headers


# ── Seed some meal logs so progress report has data ───────────────────────────
@pytest.fixture
def seeded_logs(client, auth_headers_with_profile):
    meals = [
        {"log_date": "2026-02-26", "meal_slot": "breakfast", "dish_name": "Oatmeal",        "calories": 310, "protein_g": 12, "carbs_g": 50, "fat_g": 6},
        {"log_date": "2026-02-26", "meal_slot": "lunch",     "dish_name": "Chicken Rice",   "calories": 480, "protein_g": 40, "carbs_g": 55, "fat_g": 10},
        {"log_date": "2026-02-26", "meal_slot": "dinner",    "dish_name": "Grilled Salmon", "calories": 420, "protein_g": 38, "carbs_g": 20, "fat_g": 15},
        {"log_date": "2026-02-27", "meal_slot": "lunch",     "dish_name": "Daal Rice",      "calories": 450, "protein_g": 18, "carbs_g": 65, "fat_g": 9},
        {"log_date": "2026-02-27", "meal_slot": "dinner",    "dish_name": "Karahi",         "calories": 520, "protein_g": 42, "carbs_g": 25, "fat_g": 18},
        {"log_date": "2026-02-28", "meal_slot": "breakfast", "dish_name": "Eggs Toast",     "calories": 350, "protein_g": 18, "carbs_g": 30, "fat_g": 14},
        {"log_date": "2026-02-28", "meal_slot": "lunch",     "dish_name": "Salad",          "calories": 280, "protein_g": 15, "carbs_g": 20, "fat_g": 12},
    ]
    for meal in meals:
        client.post("/meal-logs/", json=meal, headers=auth_headers_with_profile)
    return meals


# ── Mock progress report response ─────────────────────────────────────────────
def _mock_progress_report() -> ProgressReportResponse:
    return ProgressReportResponse(
        week_start          = "2026-02-26",
        week_end            = "2026-03-04",
        avg_adherence_pct   = 87.5,
        best_day            = "2026-02-26",
        worst_day           = "2026-02-27",
        patterns_identified = [
            "User consistently skips breakfast on weekdays",
            "Dinner calories are slightly above target on most days",
        ],
        recommendations     = [
            "Add a light breakfast to improve morning energy levels",
            "Consider reducing dinner portion sizes by 10-15%",
            "Your protein intake is excellent — keep it up",
        ],
        goal_progress       = "On track for fat loss goal. Weekly deficit is consistent.",
        motivational_note   = "Great consistency this week — you're building strong habits!",
        logs_analysed       = 7,
        calorie_target_used = 1800,
    )


# ═══════════════════════════════════════════════════════════════
# PROGRESS REPORT
# ═══════════════════════════════════════════════════════════════

class TestProgressReport:

    def test_requires_auth(self, client):
        r = client.post("/analytics/progress", json={})
        assert r.status_code == 401

    def test_generate_success(self, client, auth_headers_with_profile, seeded_logs):
        mock_report = _mock_progress_report()
        with patch("api.routers.analytics.generate_progress_report", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_report
            r = client.post("/analytics/progress", json={}, headers=auth_headers_with_profile)

        assert r.status_code == 200
        data = r.json()
        assert data["avg_adherence_pct"] == 87.5
        assert data["best_day"] == "2026-02-26"
        assert data["worst_day"] == "2026-02-27"
        assert len(data["patterns_identified"]) == 2
        assert len(data["recommendations"]) == 3
        assert "fat loss" in data["goal_progress"].lower()
        assert data["logs_analysed"] == 7
        assert data["calorie_target_used"] == 1800

    def test_generate_with_days_override(self, client, auth_headers_with_profile, seeded_logs):
        mock_report = _mock_progress_report()
        with patch("api.routers.analytics.generate_progress_report", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_report
            r = client.post("/analytics/progress", json={"days": 14, "calorie_target": 2000},
                            headers=auth_headers_with_profile)

        assert r.status_code == 200
        assert mock_fn.called
        # Verify payload was passed correctly
        call_kwargs = mock_fn.call_args
        request_arg = call_kwargs.kwargs.get("request") or call_kwargs.args[2]
        assert request_arg.days == 14
        assert request_arg.calorie_target == 2000

    def test_no_logs_returns_422(self, client):
        # Fresh user with no logs
        client.post("/auth/register", json={"name": "No Logs User", "password": "pass1234"})
        resp = client.post("/auth/login", json={"name": "No Logs User", "password": "pass1234"})
        h = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        with patch("api.routers.analytics.generate_progress_report", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = ValueError("No meal logs found for the last 7 days.")
            r = client.post("/analytics/progress", json={}, headers=h)

        assert r.status_code == 422
        assert "No meal logs" in r.json()["detail"]

    def test_llm_error_returns_500(self, client, auth_headers_with_profile):
        with patch("api.routers.analytics.generate_progress_report", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = Exception("LLM timeout")
            r = client.post("/analytics/progress", json={}, headers=auth_headers_with_profile)

        assert r.status_code == 500

    def test_invalid_days_value(self, client, auth_headers_with_profile):
        r = client.post("/analytics/progress", json={"days": 0}, headers=auth_headers_with_profile)
        assert r.status_code == 422

    def test_days_too_large(self, client, auth_headers_with_profile):
        r = client.post("/analytics/progress", json={"days": 100}, headers=auth_headers_with_profile)
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# LEARNED PREFERENCES — GET
# ═══════════════════════════════════════════════════════════════

class TestGetPreferences:

    def test_requires_auth(self, client):
        r = client.get("/analytics/preferences")
        assert r.status_code == 401

    def test_returns_empty_for_new_user(self, client, auth_headers):
        r = client.get("/analytics/preferences", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["liked_ingredients"] == []
        assert data["disliked_ingredients"] == []
        assert data["spice_preference"] is None
        assert data["goal_refinement"] is None

    def test_structure_is_correct(self, client, auth_headers):
        r = client.get("/analytics/preferences", headers=auth_headers)
        data = r.json()
        required_fields = [
            "liked_ingredients", "disliked_ingredients",
            "preferred_textures", "preferred_cuisines",
            "avoided_cuisines", "spice_preference",
            "goal_refinement", "session_insights",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


# ═══════════════════════════════════════════════════════════════
# LEARNED PREFERENCES — UPDATE
# ═══════════════════════════════════════════════════════════════

class TestUpdatePreferences:

    def test_requires_auth(self, client):
        r = client.put("/analytics/preferences", json={"spice_preference": "high"})
        assert r.status_code == 401

    def test_update_liked_ingredients(self, client, auth_headers):
        r = client.put("/analytics/preferences", json={
            "liked_ingredients": ["chicken", "brown rice", "spinach"],
        }, headers=auth_headers)

        assert r.status_code == 200
        assert "chicken" in r.json()["liked_ingredients"]
        assert "brown rice" in r.json()["liked_ingredients"]

    def test_update_spice_preference(self, client, auth_headers):
        r = client.put("/analytics/preferences", json={
            "spice_preference": "high",
        }, headers=auth_headers)

        assert r.status_code == 200
        assert r.json()["spice_preference"] == "high"

    def test_partial_update_preserves_other_fields(self, client, auth_headers):
        # First set liked ingredients
        client.put("/analytics/preferences", json={
            "liked_ingredients": ["lentils"],
            "spice_preference": "medium",
        }, headers=auth_headers)

        # Then update only spice_preference
        r = client.put("/analytics/preferences", json={
            "spice_preference": "low",
        }, headers=auth_headers)

        data = r.json()
        assert data["spice_preference"] == "low"
        # liked_ingredients should still be there
        assert "lentils" in data["liked_ingredients"]

    def test_update_goal_refinement(self, client, auth_headers):
        r = client.put("/analytics/preferences", json={
            "goal_refinement": "Focus on lean muscle, not aggressive bulk",
        }, headers=auth_headers)

        assert r.status_code == 200
        assert "lean muscle" in r.json()["goal_refinement"]

    def test_update_multiple_fields(self, client, auth_headers):
        r = client.put("/analytics/preferences", json={
            "liked_ingredients":    ["eggs", "avocado", "oats"],
            "disliked_ingredients": ["tofu", "celery"],
            "preferred_cuisines":   ["pakistani", "mediterranean"],
            "avoided_cuisines":     ["fast food"],
            "session_insights":     ["User prefers high-protein breakfasts"],
        }, headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert "eggs" in data["liked_ingredients"]
        assert "tofu" in data["disliked_ingredients"]
        assert "pakistani" in data["preferred_cuisines"]
        assert "fast food" in data["avoided_cuisines"]


# ═══════════════════════════════════════════════════════════════
# LEARNED PREFERENCES — RESET
# ═══════════════════════════════════════════════════════════════

class TestResetPreferences:

    def test_requires_auth(self, client):
        r = client.delete("/analytics/preferences")
        assert r.status_code == 401

    def test_reset_clears_all(self, client, auth_headers):
        # Seed some preferences
        client.put("/analytics/preferences", json={
            "liked_ingredients": ["salmon", "quinoa"],
            "spice_preference": "high",
        }, headers=auth_headers)

        # Verify they were saved
        r = client.get("/analytics/preferences", headers=auth_headers)
        assert r.json()["spice_preference"] == "high"

        # Reset
        r = client.delete("/analytics/preferences", headers=auth_headers)
        assert r.status_code == 204

        # Verify cleared
        r = client.get("/analytics/preferences", headers=auth_headers)
        data = r.json()
        assert data["liked_ingredients"] == []
        assert data["spice_preference"] is None


# ═══════════════════════════════════════════════════════════════
# LEARNING LOOP TRIGGER
# ═══════════════════════════════════════════════════════════════

class TestTriggerLearning:

    @pytest.fixture
    def feedback_id(self, client, auth_headers):
        """Seed a recipe + feedback entry for learning tests."""
        db = TestingSession()
        try:
            from db.models import Recipe as RecipeModel, RecipeNutrition
            import uuid
            from datetime import datetime

            rid = "recipe-learn-001"
            if not db.query(RecipeModel).filter_by(id=rid).first():
                db.add(RecipeModel(
                    id=rid, name="Test Recipe for Learning",
                    cuisine="pakistani", meal_type="lunch",
                    source="generated", generated_at=datetime.utcnow(),
                ))
                db.add(RecipeNutrition(
                    id=str(uuid.uuid4()), recipe_id=rid,
                    calories=450, protein_g=38, carbs_g=30, fat_g=12,
                ))
                db.commit()
        finally:
            db.close()

        r = client.post("/feedback/", json={
            "recipe_id": "recipe-learn-001",
            "rating": 2,
            "comment": "Too bland, not enough spice. Preferred something with more heat.",
        }, headers=auth_headers)
        return r.json()["feedback_id"]

    def test_requires_auth(self, client):
        r = client.post("/analytics/learn", json={"feedback_id": "some-id"})
        assert r.status_code == 401

    def test_nonexistent_feedback(self, client, auth_headers):
        with patch("api.routers.analytics.trigger_learning", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = ValueError("Feedback 'nonexistent' not found.")
            r = client.post("/analytics/learn", json={"feedback_id": "nonexistent"},
                            headers=auth_headers)

        assert r.status_code == 404

    def test_trigger_success(self, client, auth_headers, feedback_id):
        mock_response = TriggerLearningResponse(
            message             = "Learning loop completed. Preferences updated.",
            preferences_updated = True,
            goal_updated        = False,
            updated_preferences = LearnedPreferencesResponse(
                liked_ingredients    = [],
                disliked_ingredients = ["bland food"],
                preferred_textures   = [],
                preferred_cuisines   = [],
                avoided_cuisines     = [],
                spice_preference     = "high",
                goal_refinement      = None,
                session_insights     = ["User wants more spice in meals"],
            ),
        )

        with patch("api.routers.analytics.trigger_learning", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_response
            r = client.post("/analytics/learn", json={"feedback_id": feedback_id},
                            headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert data["preferences_updated"] is True
        assert data["updated_preferences"]["spice_preference"] == "high"
        assert "User wants more spice" in data["updated_preferences"]["session_insights"][0]

    def test_llm_failure_returns_500(self, client, auth_headers, feedback_id):
        with patch("api.routers.analytics.trigger_learning", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = Exception("LLM API error")
            r = client.post("/analytics/learn", json={"feedback_id": feedback_id},
                            headers=auth_headers)

        assert r.status_code == 500