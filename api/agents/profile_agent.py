"""
agents/profile_agent.py — Phase 4

Phase 4 upgrades:
- On startup: checks if user already exists in DB by name
- Returning user: loads their profile, goals, allergies, medical conditions,
  preferences, and learned_preferences from DB — skips re-entry
- New user: collects profile interactively then saves to DB
- Sets state.customer_id (user's DB primary key) for all downstream agents
- Loads learned_preferences from DB so recipe_agent benefits from past sessions
"""

from __future__ import annotations

import logging

from state import NutritionState
from schemas.nutrition_schemas import MedicalCondition, MedicalConditionType, LearnedPreferences

logger = logging.getLogger(__name__)

ACTIVITY_OPTIONS = ["sedentary", "light", "moderate", "active", "very_active"]

VALID_CONDITIONS: list[MedicalConditionType] = [
    "diabetes", "hypertension", "celiac", "lactose_intolerance",
    "kidney_disease", "heart_disease", "ibs", "anemia", "osteoporosis",
]


def _get_float(prompt: str, default: float) -> float:
    try:
        return float(input(prompt).strip())
    except ValueError:
        print(f"   ⚠️ Invalid input. Using default: {default}")
        return default


def _get_int(prompt: str, default: int) -> int:
    try:
        return int(input(prompt).strip())
    except ValueError:
        print(f"   ⚠️ Invalid input. Using default: {default}")
        return default


def _collect_medical_conditions() -> list[MedicalCondition]:
    print(f"\n   Available conditions: {', '.join(VALID_CONDITIONS)}")
    raw = input("   Any medical conditions? (comma-separated, or 'none'): ").strip().lower()
    if raw == "none" or not raw:
        return []
    conditions = []
    for item in raw.split(","):
        item = item.strip().replace(" ", "_")
        if item in VALID_CONDITIONS:
            conditions.append(MedicalCondition(condition=item))   # type: ignore[arg-type]
        else:
            print(f"   ⚠️ Unknown condition '{item}' — skipped.")
    return conditions


def _try_load_returning_user(name: str) -> dict | None:
    """
    Attempt to load a full profile from DB for a returning user.
    Returns a dict of NutritionState fields, or None if not found / DB unavailable.
    """
    try:
        from db.database import get_db
        from db.repositories import UserRepository
        from memory.progress_store import load_learned_preferences

        with get_db() as db:
            repo = UserRepository(db)
            user = repo.get_by_name(name)
            if not user:
                return None

            print(f"\n👋 Welcome back, {name}! Loading your profile...")

            profile    = user.profile
            goal       = repo.get_current_goal(user.id)
            allergies  = repo.get_allergies(user.id)
            conditions = repo.get_medical_conditions(user.id)
            prefs      = repo.get_preferences(user.id)

        learned = load_learned_preferences(user.id)

        state_data = {
            "customer_id":        user.id,
            "name":               user.name,
            "age":                profile.age         if profile else None,
            "gender":             profile.gender      if profile else None,
            "weight_kg":          profile.weight_kg   if profile else None,
            "height_cm":          profile.height_cm   if profile else None,
            "activity_level":     profile.activity_level if profile else None,
            "allergies":          allergies,
            "medical_conditions": conditions,
            "preferences":        prefs,
            "fitness_goal":       goal.goal_type      if goal else None,
            "learned_preferences": learned,
            "profile_collected":  True,
        }

        if profile:
            print(f"   ✅ Age {profile.age} | {profile.weight_kg}kg | {profile.height_cm}cm | {profile.activity_level}")
        if goal:
            print(f"   ✅ Goal: {goal.goal_type} | Target: {goal.calorie_target} kcal")
        if allergies:
            print(f"   ✅ Allergies: {', '.join(allergies)}")
        if conditions:
            print(f"   ✅ Conditions: {', '.join(c.condition for c in conditions)}")
        if learned:
            print(f"   ✅ Learned preferences loaded from previous sessions.")

        return state_data

    except Exception as e:
        logger.warning("Could not load returning user from DB (%s). Treating as new user.", e)
        return None


def _save_new_user(state: NutritionState) -> str | None:
    """
    Persist a newly collected profile to the DB.
    Returns the new user_id, or None if DB unavailable.
    """
    try:
        from db.database import get_db
        from db.repositories import UserRepository

        with get_db() as db:
            repo = UserRepository(db)
            user, created = repo.get_or_create(state.name)

            repo.upsert_profile(
                user_id=user.id,
                age=state.age,
                gender=state.gender,
                weight_kg=state.weight_kg,
                height_cm=state.height_cm,
                activity_level=state.activity_level,
            )
            repo.sync_allergies(user.id, state.allergies)
            repo.sync_medical_conditions(user.id, state.medical_conditions)

            for key, value in state.preferences.items():
                repo.upsert_preference(user.id, key, str(value))

        print(f"   💾 Profile saved to database (user_id: {user.id[:8]}...)")
        return user.id

    except Exception as e:
        logger.warning("Could not save new user to DB (%s). Profile exists only in memory.", e)
        return None


def profile_agent_node(state: NutritionState) -> NutritionState:
    print("\n👤 Collecting Customer Profile...")

    # ── Name first — check if returning user ─────────────────────────────────
    name = input("Enter your name: ").strip()
    while not name:
        name = input("⚠️ Name cannot be empty: ").strip()

    # ── Try loading from DB ───────────────────────────────────────────────────
    existing = _try_load_returning_user(name)
    if existing:
        # Returning user — ask if they want to update anything
        update = input("\n🔄 Update your profile? (y/n): ").strip().lower()
        if update != "y":
            return NutritionState(**existing)
        # Fall through to re-collect profile

    # ── New user (or returning user requesting update) ────────────────────────
    age       = _get_int("Age: ", default=25)
    weight_kg = _get_float("Weight (kg): ", default=70.0)
    height_cm = _get_float("Height (cm): ", default=170.0)

    gender_raw = input("Gender (male/female): ").strip().lower()
    gender     = gender_raw if gender_raw in ("male", "female") else "male"

    print(f"Activity options: {', '.join(ACTIVITY_OPTIONS)}")
    activity_raw   = input("Activity level: ").strip().lower().replace(" ", "_")
    activity_level = activity_raw if activity_raw in ACTIVITY_OPTIONS else "moderate"

    print("\n⚕️  Medical Conditions")
    medical_conditions = _collect_medical_conditions()

    allergies_raw = input("\nAllergies (comma-separated, or 'none'): ").strip()
    allergies = (
        [a.strip() for a in allergies_raw.split(",")]
        if allergies_raw.lower() != "none" else []
    )

    fitness_goal = input("\nFitness goal (e.g., muscle gain, weight loss, maintenance): ").strip()
    while not fitness_goal:
        fitness_goal = input("⚠️ Please specify a fitness goal: ").strip()

    spice_level = input("Preferred spice level (Low / Medium / High): ").strip().capitalize()
    if spice_level not in ("Low", "Medium", "High"):
        spice_level = "Medium"

    cuisine = input("Preferred cuisine (e.g., Pakistani, Indian, Italian): ").strip() or "any"
    preferences = {"spice_level": spice_level, "cuisine": cuisine.lower()}

    print(f"\n✅ Profile collected for {name}.")

    new_state = NutritionState(
        name=name,
        age=age,
        gender=gender,
        weight_kg=weight_kg,
        height_cm=height_cm,
        activity_level=activity_level,
        medical_conditions=medical_conditions,
        allergies=allergies,
        preferences=preferences,
        fitness_goal=fitness_goal,
        profile_collected=True,
        # Carry forward learned prefs if they loaded from a returning user
        learned_preferences=existing.get("learned_preferences") if existing else None,
    )

    # ── Persist to DB ─────────────────────────────────────────────────────────
    user_id = _save_new_user(new_state)
    if user_id:
        return new_state.model_copy(update={"customer_id": user_id})

    return new_state