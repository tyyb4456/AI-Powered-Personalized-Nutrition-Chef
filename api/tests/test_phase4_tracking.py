"""
tests/test_phase4_tracking.py

Tests for Phase 4 — feedback and meal log endpoints.
No LLM calls — pure DB read/write via SQLite.

Run with:
  pytest tests/test_phase4_tracking.py -v
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
from app import create_app
from dependencies import get_db

# ── SQLite test DB ────────────────────────────────────────────────────────────
SQLITE_URL = "sqlite:///./test_tracking.db"
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
    client.post("/auth/register", json={"name": "Tracker User", "password": "pass1234"})
    resp = client.post("/auth/login", json={"name": "Tracker User", "password": "pass1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Seed a fake recipe into DB for feedback tests ─────────────────────────────
@pytest.fixture
def saved_recipe_id(client, auth_headers):
    """
    Seed a recipe row directly via the DB so feedback tests have a valid recipe_id.
    We mock the generate service since we don't want a real LLM call.
    """
    from schemas.recipe_schemas import (
        RecipeResponse, NutritionOut, ValidationOut,
    )
    mock_response = RecipeResponse(
        recipe_id         = "recipe-001",
        dish_name         = "Test Chicken",
        cuisine           = "pakistani",
        meal_type         = "lunch",
        prep_time_minutes = 30,
        ingredients       = [{"name": "Chicken", "quantity": "200g"}],
        steps             = ["Cook it."],
        nutrition         = NutritionOut(calories=450, protein_g=40, carbs_g=30, fat_g=12),
        substitutions     = [],
        explanation       = "Good for muscle gain.",
        validation        = ValidationOut(
            passed=True, calorie_check=True, protein_check=True,
            carbs_check=True, fat_check=True, fiber_check=True,
            allergen_check=True, calorie_diff_pct=1.0, notes="All good."
        ),
        calorie_target    = 2800,
        macro_split       = {"protein": 35, "carbs": 40, "fat": 25},
    )
    with patch("api.routers.recipes.generate_recipe") as mock_gen:
        mock_gen.return_value = mock_response
        # Actually insert the recipe into DB via service directly
        # We'll use the returned recipe_id from mock
        pass

    # Insert recipe directly to SQLite via repo
    db = TestingSession()
    try:
        from db.models import Recipe as RecipeModel, RecipeNutrition
        import uuid
        from datetime import datetime

        rid = "recipe-test-001"
        db.add(RecipeModel(
            id="recipe-test-001", name="Test Chicken",
            cuisine="pakistani", meal_type="lunch",
            source="generated", generated_at=datetime.utcnow(),
        ))
        db.add(RecipeNutrition(
            id=str(uuid.uuid4()), recipe_id=rid,
            calories=450, protein_g=40.0, carbs_g=30.0, fat_g=12.0,
        ))
        db.commit()
        return rid
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# FEEDBACK — SUBMIT
# ═══════════════════════════════════════════════════════════════

class TestSubmitFeedback:

    def test_submit_requires_auth(self, client, saved_recipe_id):
        r = client.post("/feedback/", json={
            "recipe_id": saved_recipe_id, "rating": 5,
        })
        assert r.status_code == 401

    def test_submit_success(self, client, auth_headers, saved_recipe_id):
        r = client.post("/feedback/", json={
            "recipe_id": saved_recipe_id,
            "rating":    4,
            "comment":   "Really enjoyed the spice level!",
        }, headers=auth_headers)

        assert r.status_code == 201
        data = r.json()
        assert data["recipe_id"] == saved_recipe_id
        assert data["rating"] == 4
        assert data["comment"] == "Really enjoyed the spice level!"
        assert "feedback_id" in data
        assert "created_at" in data

    def test_submit_without_comment(self, client, auth_headers, saved_recipe_id):
        r = client.post("/feedback/", json={
            "recipe_id": saved_recipe_id,
            "rating":    3,
        }, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["comment"] is None

    def test_submit_invalid_rating_too_high(self, client, auth_headers, saved_recipe_id):
        r = client.post("/feedback/", json={
            "recipe_id": saved_recipe_id, "rating": 6,
        }, headers=auth_headers)
        assert r.status_code == 422

    def test_submit_invalid_rating_zero(self, client, auth_headers, saved_recipe_id):
        r = client.post("/feedback/", json={
            "recipe_id": saved_recipe_id, "rating": 0,
        }, headers=auth_headers)
        assert r.status_code == 422

    def test_submit_nonexistent_recipe(self, client, auth_headers):
        r = client.post("/feedback/", json={
            "recipe_id": "nonexistent-recipe-id", "rating": 5,
        }, headers=auth_headers)
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════
# FEEDBACK — LIST & DELETE
# ═══════════════════════════════════════════════════════════════

class TestListDeleteFeedback:

    def test_list_requires_auth(self, client):
        r = client.get("/feedback/")
        assert r.status_code == 401

    def test_list_returns_submitted_feedback(self, client, auth_headers, saved_recipe_id):
        # Submit first
        client.post("/feedback/", json={
            "recipe_id": saved_recipe_id, "rating": 5, "comment": "Perfect!",
        }, headers=auth_headers)

        r = client.get("/feedback/", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any(f["recipe_id"] == saved_recipe_id for f in data["feedback"])

    def test_delete_feedback(self, client, auth_headers, saved_recipe_id):
        # Submit then delete
        resp = client.post("/feedback/", json={
            "recipe_id": saved_recipe_id, "rating": 2,
        }, headers=auth_headers)
        fid = resp.json()["feedback_id"]

        r = client.delete(f"/feedback/{fid}", headers=auth_headers)
        assert r.status_code == 204

    def test_delete_nonexistent_feedback(self, client, auth_headers):
        r = client.delete("/feedback/nonexistent-id", headers=auth_headers)
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════
# MEAL LOGS — LOG
# ═══════════════════════════════════════════════════════════════

class TestLogMeal:

    def test_log_requires_auth(self, client):
        r = client.post("/meal-logs/", json={
            "log_date": "2026-03-01", "meal_slot": "lunch",
            "dish_name": "Daal Rice", "calories": 450,
            "protein_g": 18.0, "carbs_g": 65.0, "fat_g": 8.0,
        })
        assert r.status_code == 401

    def test_log_success(self, client, auth_headers):
        r = client.post("/meal-logs/", json={
            "log_date":  "2026-03-01",
            "meal_slot": "lunch",
            "dish_name": "Daal Mash with Brown Rice",
            "planned":   True,
            "calories":  420,
            "protein_g": 18.0,
            "carbs_g":   55.0,
            "fat_g":     10.0,
            "source":    "plan",
        }, headers=auth_headers)

        assert r.status_code == 201
        data = r.json()
        assert data["dish_name"] == "Daal Mash with Brown Rice"
        assert data["meal_slot"] == "lunch"
        assert data["calories"] == 420
        assert data["planned"] is True
        assert "log_id" in data
        assert "logged_at" in data

    def test_log_invalid_slot(self, client, auth_headers):
        r = client.post("/meal-logs/", json={
            "log_date": "2026-03-01", "meal_slot": "teatime",
            "dish_name": "Biscuits", "calories": 200,
            "protein_g": 3.0, "carbs_g": 30.0, "fat_g": 8.0,
        }, headers=auth_headers)
        assert r.status_code == 400

    def test_log_invalid_date(self, client, auth_headers):
        r = client.post("/meal-logs/", json={
            "log_date": "not-a-date", "meal_slot": "lunch",
            "dish_name": "Test", "calories": 300,
            "protein_g": 10.0, "carbs_g": 40.0, "fat_g": 8.0,
        }, headers=auth_headers)
        assert r.status_code == 400

    def test_log_negative_calories(self, client, auth_headers):
        r = client.post("/meal-logs/", json={
            "log_date": "2026-03-01", "meal_slot": "dinner",
            "dish_name": "Mystery Food", "calories": -100,
            "protein_g": 5.0, "carbs_g": 10.0, "fat_g": 2.0,
        }, headers=auth_headers)
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# MEAL LOGS — LIST, DELETE, ADHERENCE
# ═══════════════════════════════════════════════════════════════

class TestListDeleteLogs:

    def test_list_requires_auth(self, client):
        r = client.get("/meal-logs/")
        assert r.status_code == 401

    def test_list_empty(self, client):
        # New user with no logs
        client.post("/auth/register", json={"name": "Empty Logger", "password": "pass1234"})
        resp = client.post("/auth/login", json={"name": "Empty Logger", "password": "pass1234"})
        h = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        r = client.get("/meal-logs/", headers=h)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_list_after_logging(self, client, auth_headers):
        client.post("/meal-logs/", json={
            "log_date": "2026-03-01", "meal_slot": "breakfast",
            "dish_name": "Oatmeal", "calories": 300,
            "protein_g": 10.0, "carbs_g": 50.0, "fat_g": 5.0,
        }, headers=auth_headers)

        r = client.get("/meal-logs/?days=7", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_filter_by_slot(self, client, auth_headers):
        r = client.get("/meal-logs/?meal_slot=breakfast", headers=auth_headers)
        assert r.status_code == 200
        # All returned logs should be breakfast
        for log in r.json()["logs"]:
            assert log["meal_slot"] == "breakfast"

    def test_delete_log(self, client, auth_headers):
        resp = client.post("/meal-logs/", json={
            "log_date": "2026-03-02", "meal_slot": "snack",
            "dish_name": "Apple", "calories": 95,
            "protein_g": 0.5, "carbs_g": 25.0, "fat_g": 0.3,
        }, headers=auth_headers)
        log_id = resp.json()["log_id"]

        r = client.delete(f"/meal-logs/{log_id}", headers=auth_headers)
        assert r.status_code == 204

    def test_delete_nonexistent_log(self, client, auth_headers):
        r = client.delete("/meal-logs/nonexistent-id", headers=auth_headers)
        assert r.status_code == 404


class TestAdherence:

    def test_adherence_requires_auth(self, client):
        r = client.get("/meal-logs/adherence")
        assert r.status_code == 401

    def test_adherence_returns_list(self, client, auth_headers):
        r = client.get("/meal-logs/adherence?days=7", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_adherence_with_calorie_override(self, client, auth_headers):
        r = client.get("/meal-logs/adherence?days=7&calorie_target=2000", headers=auth_headers)
        assert r.status_code == 200

    def test_adherence_structure(self, client, auth_headers):
        # Log a meal first so we have data
        client.post("/meal-logs/", json={
            "log_date": "2026-03-01", "meal_slot": "dinner",
            "dish_name": "Grilled Salmon", "calories": 520,
            "protein_g": 45.0, "carbs_g": 20.0, "fat_g": 22.0,
        }, headers=auth_headers)

        r = client.get("/meal-logs/adherence?days=30&calorie_target=2000", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        if data:  # may be empty if logs are outside range
            entry = data[0]
            assert "log_date" in entry
            assert "planned_calories" in entry
            assert "actual_calories" in entry
            assert "adherence_pct" in entry
            assert "meals_logged" in entry