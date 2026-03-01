"""
tests/test_phase3_meal_plans.py

Tests for Phase 3 meal plan endpoints.
The heavy pipeline (90-180s) is mocked so tests run fast and offline.

Run with:
  pytest tests/test_phase3_meal_plans.py -v
"""

from __future__ import annotations

import pytest
from datetime import date
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
from app import create_app
from dependencies import get_db
from schemas.meal_plan_schemas import (
    MealPlanResponse, DayPlanOut, MealSlotOut, WeeklySummaryOut,
    GroceryListOut, GroceryItemOut, PrepScheduleOut, PrepTaskOut,
    MealPlanSummary,
)

# ── SQLite test DB ────────────────────────────────────────────────────────────
SQLITE_URL = "sqlite:///./test_meal_plans.db"
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
    client.post("/auth/register", json={"name": "Plan Tester", "password": "pass1234"})
    resp = client.post("/auth/login", json={"name": "Plan Tester", "password": "pass1234"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_with_profile(client, auth_headers):
    client.put("/users/me", json={
        "age": 30, "gender": "female", "weight_kg": 65.0,
        "height_cm": 165.0, "activity_level": "active",
        "fitness_goal": "fat_loss", "cuisine": "pakistani",
        "spice_level": "medium",
    }, headers=auth_headers)
    return auth_headers


# ── Mock full plan response ───────────────────────────────────────────────────

def _mock_meal_plan() -> MealPlanResponse:
    days = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in day_names:
        meals = [
            MealSlotOut(slot="breakfast", dish_name=f"{day} Oatmeal",   cuisine="any", calories=350, protein_g=15, carbs_g=55, fat_g=8,  fiber_g=5),
            MealSlotOut(slot="lunch",     dish_name=f"{day} Daal Rice",  cuisine="pakistani", calories=480, protein_g=22, carbs_g=68, fat_g=12, fiber_g=8),
            MealSlotOut(slot="dinner",    dish_name=f"{day} Grilled Ch", cuisine="pakistani", calories=420, protein_g=40, carbs_g=28, fat_g=10, fiber_g=4),
            MealSlotOut(slot="snack",     dish_name=f"{day} Apple",      cuisine="any", calories=95,  protein_g=1,  carbs_g=22, fat_g=0,  fiber_g=3),
        ]
        days.append(DayPlanOut(
            day=day, meals=meals,
            total_calories=1345, total_protein_g=78, total_carbs_g=173, total_fat_g=30, total_fiber_g=20,
        ))

    summary = WeeklySummaryOut(
        avg_daily_calories=1345, avg_daily_protein_g=78, avg_daily_carbs_g=173,
        avg_daily_fat_g=30, avg_daily_fiber_g=20, total_weekly_calories=9415,
        calorie_target_hit_days=6, notes="On track for fat loss goal.",
    )
    grocery = GroceryListOut(
        items=[
            GroceryItemOut(name="Chicken Breast", total_quantity="1.4kg", category="protein", estimated_cost_pkr=1400),
            GroceryItemOut(name="Brown Rice",     total_quantity="700g",  category="pantry",  estimated_cost_pkr=210),
            GroceryItemOut(name="Oats",           total_quantity="500g",  category="pantry",  estimated_cost_pkr=150),
        ],
        total_items=3,
        estimated_total_cost_pkr=1760,
        shopping_notes="Shop Sunday morning for best freshness.",
        by_category={
            "protein": [GroceryItemOut(name="Chicken Breast", total_quantity="1.4kg", category="protein")],
            "pantry":  [GroceryItemOut(name="Brown Rice",     total_quantity="700g",  category="pantry")],
        },
    )
    prep = PrepScheduleOut(
        tasks=[
            PrepTaskOut(
                task="Cook 700g brown rice", prep_day="Sunday",
                duration_minutes=30, covers_meals=["Monday Daal Rice", "Tuesday Daal Rice"],
                storage_instruction="Refrigerate in airtight container, use within 4 days.",
                reheating_tip="Microwave with a splash of water.",
            )
        ],
        total_prep_time_min=90,
        prep_days=["Sunday", "Wednesday"],
        efficiency_notes="Saves approximately 2 hours of daily cooking.",
    )
    return MealPlanResponse(
        plan_id="test-plan-001",
        week_start="2026-03-02",
        status="active",
        days=days,
        weekly_summary=summary,
        calorie_target=1800,
        macro_split={"protein": 35, "carbs": 30, "fat": 35},
        grocery_list=grocery,
        prep_schedule=prep,
    )


# ═══════════════════════════════════════════════════════════════
# GENERATE
# ═══════════════════════════════════════════════════════════════

class TestGenerateMealPlan:

    def test_generate_requires_auth(self, client):
        r = client.post("/meal-plans/generate", json={})
        assert r.status_code == 401

    def test_generate_success(self, client, auth_headers_with_profile):
        mock_plan = _mock_meal_plan()
        with patch("api.routers.meal_plans.generate_meal_plan", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_plan
            r = client.post("/meal-plans/generate", json={}, headers=auth_headers_with_profile)

        assert r.status_code == 201
        data = r.json()
        assert data["plan_id"] == "test-plan-001"
        assert data["week_start"] == "2026-03-02"
        assert len(data["days"]) == 7
        assert data["days"][0]["day"] == "Monday"
        assert len(data["days"][0]["meals"]) == 4
        assert data["weekly_summary"]["calorie_target_hit_days"] == 6
        assert data["grocery_list"]["total_items"] == 3
        assert len(data["prep_schedule"]["tasks"]) == 1

    def test_generate_with_overrides(self, client, auth_headers_with_profile):
        mock_plan = _mock_meal_plan()
        with patch("api.routers.meal_plans.generate_meal_plan", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_plan
            r = client.post("/meal-plans/generate", json={
                "fitness_goal": "muscle_gain",
                "cuisine": "italian",
                "week_start": "2026-03-09",
            }, headers=auth_headers_with_profile)

        assert r.status_code == 201
        assert mock_fn.called

    def test_generate_pipeline_failure_returns_500(self, client, auth_headers_with_profile):
        with patch("api.routers.meal_plans.generate_meal_plan", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = Exception("LLM quota exceeded")
            r = client.post("/meal-plans/generate", json={}, headers=auth_headers_with_profile)

        assert r.status_code == 500

    def test_generate_value_error_returns_422(self, client, auth_headers_with_profile):
        with patch("api.routers.meal_plans.generate_meal_plan", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = ValueError("No profile data")
            r = client.post("/meal-plans/generate", json={}, headers=auth_headers_with_profile)

        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# LIST PLANS
# ═══════════════════════════════════════════════════════════════

class TestListPlans:

    def test_list_requires_auth(self, client):
        r = client.get("/meal-plans/")
        assert r.status_code == 401

    def test_list_empty(self, client, auth_headers):
        with patch("api.routers.meal_plans.list_user_plans", return_value=[]):
            r = client.get("/meal-plans/", headers=auth_headers)

        assert r.status_code == 200
        assert r.json() == []

    def test_list_with_data(self, client, auth_headers):
        summaries = [
            MealPlanSummary(plan_id="p1", week_start="2026-03-02", status="active",
                            avg_daily_calories=1800, calorie_target_hit_days=5),
            MealPlanSummary(plan_id="p2", week_start="2026-02-23", status="archived",
                            avg_daily_calories=1750, calorie_target_hit_days=4),
        ]
        with patch("api.routers.meal_plans.list_user_plans", return_value=summaries):
            r = client.get("/meal-plans/", headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert data[0]["plan_id"] == "p1"
        assert data[0]["status"] == "active"


# ═══════════════════════════════════════════════════════════════
# GET ACTIVE
# ═══════════════════════════════════════════════════════════════

class TestGetActivePlan:

    def test_get_active_requires_auth(self, client):
        r = client.get("/meal-plans/active")
        assert r.status_code == 401

    def test_get_active_not_found(self, client, auth_headers):
        with patch("api.routers.meal_plans.get_active_plan", return_value=None):
            r = client.get("/meal-plans/active", headers=auth_headers)

        assert r.status_code == 404
        assert "No active meal plan" in r.json()["detail"]

    def test_get_active_success(self, client, auth_headers):
        mock_plan = _mock_meal_plan()
        with patch("api.routers.meal_plans.get_active_plan", return_value=mock_plan):
            r = client.get("/meal-plans/active", headers=auth_headers)

        assert r.status_code == 200
        assert r.json()["plan_id"] == "test-plan-001"
        assert r.json()["status"] == "active"


# ═══════════════════════════════════════════════════════════════
# GROCERY & PREP (inline in generate response)
# ═══════════════════════════════════════════════════════════════

class TestGroceryAndPrep:

    def test_grocery_in_generate_response(self, client, auth_headers_with_profile):
        mock_plan = _mock_meal_plan()
        with patch("api.routers.meal_plans.generate_meal_plan", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_plan
            r = client.post("/meal-plans/generate", json={}, headers=auth_headers_with_profile)

        data = r.json()
        assert data["grocery_list"] is not None
        assert data["grocery_list"]["total_items"] == 3
        assert "protein" in data["grocery_list"]["by_category"]

    def test_prep_in_generate_response(self, client, auth_headers_with_profile):
        mock_plan = _mock_meal_plan()
        with patch("api.routers.meal_plans.generate_meal_plan", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_plan
            r = client.post("/meal-plans/generate", json={}, headers=auth_headers_with_profile)

        data = r.json()
        assert data["prep_schedule"] is not None
        assert data["prep_schedule"]["total_prep_time_min"] == 90
        assert "Sunday" in data["prep_schedule"]["prep_days"]
        assert len(data["prep_schedule"]["tasks"]) == 1

    def test_grocery_endpoint_not_found_for_old_plan(self, client, auth_headers):
        """Grocery data isn't stored in DB — only available inline from generate."""
        r = client.get("/meal-plans/nonexistent-id/grocery", headers=auth_headers)
        assert r.status_code == 404

    def test_prep_endpoint_not_found_for_old_plan(self, client, auth_headers):
        r = client.get("/meal-plans/nonexistent-id/prep", headers=auth_headers)
        assert r.status_code == 404