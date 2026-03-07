"""
tests/test_phase2_recipes.py

Tests for Phase 2 recipe endpoints.
The LLM pipeline is mocked so tests run fast and offline.

Run with:
  pytest tests/test_phase2_recipes.py -v
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
from schemas.recipe_schemas import (
    RecipeResponse, NutritionOut, ValidationOut, RecipeListResponse,
)

# ── In-memory SQLite for tests ────────────────────────────────────────────────
SQLITE_URL = "sqlite:///./test_recipes.db"
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
    """Register + login, return Authorization headers."""
    client.post("/auth/register", json={
        "name": "Recipe Tester",
        "password": "pass1234"
    })
    resp = client.post("/auth/login", json={
        "name": "Recipe Tester",
        "password": "pass1234"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_with_profile(client, auth_headers):
    """Auth headers for a user with a full profile saved."""
    client.put("/users/me", json={
        "age": 28,
        "gender": "male",
        "weight_kg": 80.0,
        "height_cm": 175.0,
        "activity_level": "moderate",
        "fitness_goal": "muscle_gain",
        "cuisine": "pakistani",
        "spice_level": "medium",
        "allergies": [],
        "medical_conditions": [],
    }, headers=auth_headers)
    return auth_headers


# ── Mock recipe response ──────────────────────────────────────────────────────

def _mock_recipe_response() -> RecipeResponse:
    return RecipeResponse(
        recipe_id         = "test-recipe-id-001",
        dish_name         = "Grilled Chicken with Brown Rice",
        cuisine           = "pakistani",
        meal_type         = "lunch",
        prep_time_minutes = 30,
        ingredients       = [
            {"name": "Chicken Breast", "quantity": "200g"},
            {"name": "Brown Rice",     "quantity": "100g"},
        ],
        steps             = ["Marinate chicken.", "Grill for 20 mins.", "Serve with rice."],
        nutrition         = NutritionOut(
            calories=520, protein_g=45.0, carbs_g=40.0, fat_g=12.0, fiber_g=6.0
        ),
        substitutions     = [],
        explanation       = "This recipe is high in protein to support your muscle gain goal.",
        validation        = ValidationOut(
            passed=True, calorie_check=True, protein_check=True,
            carbs_check=True, fat_check=True, fiber_check=True,
            allergen_check=True, calorie_diff_pct=2.1, notes="All checks passed."
        ),
        calorie_target    = 2800,
        macro_split       = {"protein": 35, "carbs": 40, "fat": 25},
        from_cache        = False,
    )


# ═══════════════════════════════════════════════════════════════
# GENERATE RECIPE
# ═══════════════════════════════════════════════════════════════

class TestGenerateRecipe:

    def test_generate_requires_auth(self, client):
        r = client.post("/recipes/generate", json={})
        assert r.status_code == 401

    def test_generate_success(self, client, auth_headers_with_profile):
        """Full happy-path — service is mocked, pipeline skipped."""
        mock_response = _mock_recipe_response()

        with patch("api.routers.recipes.generate_recipe", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            r = client.post("/recipes/generate", json={}, headers=auth_headers_with_profile)

        assert r.status_code == 201
        data = r.json()
        assert data["dish_name"] == "Grilled Chicken with Brown Rice"
        assert data["recipe_id"] == "test-recipe-id-001"
        assert data["nutrition"]["calories"] == 520
        assert data["validation"]["passed"] is True
        assert "explanation" in data

    def test_generate_with_overrides(self, client, auth_headers_with_profile):
        """Override cuisine and fitness_goal in the request."""
        mock_response = _mock_recipe_response()

        with patch("api.routers.recipes.generate_recipe", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            r = client.post("/recipes/generate", json={
                "fitness_goal": "fat_loss",
                "cuisine": "italian",
                "meal_type": "dinner",
            }, headers=auth_headers_with_profile)

        assert r.status_code == 201
        # Verify the service was called (with the right user)
        assert mock_gen.called

    def test_generate_pipeline_error_returns_500(self, client, auth_headers_with_profile):
        with patch("api.routers.recipes.generate_recipe", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = Exception("LLM timeout")

            r = client.post("/recipes/generate", json={}, headers=auth_headers_with_profile)

        assert r.status_code == 500
        assert "failed" in r.json()["error"].lower()

    def test_generate_value_error_returns_422(self, client, auth_headers_with_profile):
        with patch("api.routers.recipes.generate_recipe", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = ValueError("No profile data available")

            r = client.post("/recipes/generate", json={}, headers=auth_headers_with_profile)

        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# GET RECIPE BY ID
# ═══════════════════════════════════════════════════════════════

class TestGetRecipe:

    def test_get_recipe_requires_auth(self, client):
        r = client.get("/recipes/some-id")
        assert r.status_code == 401

    def test_get_recipe_not_found(self, client, auth_headers):
        with patch("api.routers.recipes.get_recipe_by_id", return_value=None):
            r = client.get("/recipes/nonexistent-id", headers=auth_headers)
        assert r.status_code == 404

    def test_get_recipe_success(self, client, auth_headers):
        from schemas.recipe_schemas import RecipeSummary
        mock_summary = RecipeSummary(
            recipe_id="abc123",
            dish_name="Daal Mash",
            cuisine="pakistani",
            meal_type="lunch",
            calories=420,
            protein_g=18.0,
            carbs_g=55.0,
            fat_g=10.0,
        )

        with patch("api.routers.recipes.get_recipe_by_id", return_value=mock_summary):
            r = client.get("/recipes/abc123", headers=auth_headers)

        assert r.status_code == 200
        assert r.json()["dish_name"] == "Daal Mash"
        assert r.json()["calories"] == 420


# ═══════════════════════════════════════════════════════════════
# LIST RECIPES
# ═══════════════════════════════════════════════════════════════

class TestListRecipes:

    def test_list_requires_auth(self, client):
        r = client.get("/recipes/")
        assert r.status_code == 401

    def test_list_returns_empty(self, client, auth_headers):
        from schemas.recipe_schemas import RecipeListResponse
        mock_list = RecipeListResponse(recipes=[], total=0, page=1, limit=10)

        with patch("api.routers.recipes.list_user_recipes", return_value=mock_list):
            r = client.get("/recipes/", headers=auth_headers)

        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["recipes"] == []

    def test_list_pagination_params(self, client, auth_headers):
        from schemas.recipe_schemas import RecipeListResponse
        mock_list = RecipeListResponse(recipes=[], total=0, page=2, limit=5)

        with patch("api.routers.recipes.list_user_recipes", return_value=mock_list) as mock_fn:
            r = client.get("/recipes/?page=2&limit=5", headers=auth_headers)

        assert r.status_code == 200

    def test_list_invalid_limit(self, client, auth_headers):
        """limit > 50 should be rejected by query validation."""
        r = client.get("/recipes/?limit=200", headers=auth_headers)
        assert r.status_code == 422