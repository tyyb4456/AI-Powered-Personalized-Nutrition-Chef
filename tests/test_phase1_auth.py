"""
tests/test_phase1_auth.py

Integration tests for Phase 1 — auth and user profile endpoints.

Run with:
  pytest tests/test_phase1_auth.py -v

Uses an in-memory SQLite DB (no PostgreSQL needed for testing).
The fixture patches SessionLocal to use SQLite so tests are isolated.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
from api.main import create_app
from api.dependencies import get_db


# ── In-memory SQLite DB ───────────────────────────────────────────────────────

SQLITE_URL = "sqlite:///./test_nutrition.db"

engine_test = create_engine(
    SQLITE_URL, connect_args={"check_same_thread": False}
)
TestingSession = sessionmaker(
    bind=engine_test, autocommit=False, autoflush=False, expire_on_commit=False
)


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


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ═══════════════════════════════════════════════════════════════
# REGISTER
# ═══════════════════════════════════════════════════════════════

def test_register_success(client):
    r = client.post("/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "securepass123"
    })
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["name"] == "Test User"
    assert data["token_type"] == "bearer"


def test_register_duplicate_name(client):
    client.post("/auth/register", json={
        "name": "Duplicate User",
        "password": "pass123"
    })
    r = client.post("/auth/register", json={
        "name": "Duplicate User",
        "password": "anotherpass"
    })
    assert r.status_code == 409


def test_register_short_password(client):
    r = client.post("/auth/register", json={
        "name": "Weak Pass User",
        "password": "abc"
    })
    assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════

def test_login_success(client):
    client.post("/auth/register", json={"name": "Login User", "password": "pass1234"})
    r = client.post("/auth/login", json={"name": "Login User", "password": "pass1234"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={"name": "WrongPass User", "password": "correct"})
    r = client.post("/auth/login", json={"name": "WrongPass User", "password": "wrong"})
    assert r.status_code == 401


def test_login_nonexistent_user(client):
    r = client.post("/auth/login", json={"name": "Nobody", "password": "pass"})
    assert r.status_code == 401


# ═══════════════════════════════════════════════════════════════
# GET /users/me
# ═══════════════════════════════════════════════════════════════

def test_get_profile_authenticated(client):
    r_reg = client.post("/auth/register", json={"name": "Profile User", "password": "pass1234"})
    token = r_reg.json()["access_token"]
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Profile User"
    assert data["allergies"] == []
    assert data["medical_conditions"] == []


def test_get_profile_unauthenticated(client):
    r = client.get("/users/me")
    assert r.status_code == 401


def test_get_profile_invalid_token(client):
    r = client.get("/users/me", headers={"Authorization": "Bearer bad.token.here"})
    assert r.status_code == 401


# ═══════════════════════════════════════════════════════════════
# PUT /users/me
# ═══════════════════════════════════════════════════════════════

def test_update_profile(client):
    r_reg = client.post("/auth/register", json={"name": "Update User", "password": "pass1234"})
    token = r_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.put("/users/me", json={
        "age": 28,
        "gender": "male",
        "weight_kg": 75.5,
        "height_cm": 178.0,
        "activity_level": "moderate",
        "fitness_goal": "muscle_gain",
        "allergies": ["nuts", "dairy"],
        "medical_conditions": ["hypertension"],
        "cuisine": "pakistani",
        "spice_level": "medium",
    }, headers=headers)

    assert r.status_code == 200
    data = r.json()
    assert data["age"] == 28
    assert data["weight_kg"] == 75.5
    assert "nuts" in data["allergies"]
    assert "hypertension" in data["medical_conditions"]
    assert data["preferences"]["cuisine"] == "pakistani"
    assert data["preferences"]["fitness_goal"] == "muscle_gain"


def test_update_invalid_medical_condition(client):
    r_reg = client.post("/auth/register", json={"name": "Bad Cond User", "password": "pass1234"})
    token = r_reg.json()["access_token"]
    r = client.put("/users/me", json={
        "medical_conditions": ["cancer"]  # not in valid list
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_update_invalid_activity_level(client):
    r_reg = client.post("/auth/register", json={"name": "Bad Act User", "password": "pass1234"})
    token = r_reg.json()["access_token"]
    r = client.put("/users/me", json={
        "activity_level": "superhuman"
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400