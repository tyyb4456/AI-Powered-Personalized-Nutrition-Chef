"""
agents/profile_agent.py

Phase 2 upgrades:
- Collects medical conditions (diabetes, hypertension, etc.)
- Input validation for all numeric fields
- hardcoded test values — proper interactive CLI is in comments
- Returns NutritionState (profile is entry point, initialises full state)
"""

from state import NutritionState
from schemas.nutrition_schemas import MedicalCondition, MedicalConditionType

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
            conditions.append(MedicalCondition(condition=item))  # type: ignore[arg-type]
        else:
            print(f"   ⚠️ Unknown condition '{item}' — skipped.")

    return conditions

def profile_agent_node(state: NutritionState) -> NutritionState:
    print("\n👤 Collecting Customer Profile...")

    # ── Name ─────────────────────────────────────────────────────────────────
    # name = input("Enter customer name: ").strip()
    name = "tayyab"
    while not name:
        name = input("⚠️ Name cannot be empty: ").strip()

    # ── Basic stats ───────────────────────────────────────────────────────────
    # age       = _get_int("Age: ", default=25)
    age = 22
    # weight_kg = _get_float("Weight (kg): ", default=70.0)
    weight_kg = 56
    # height_cm = _get_float("Height (cm): ", default=170.0)
    height_cm = 189

    # gender_raw = input("Gender (male/female): ").strip().lower()
    gender_raw = "male"
    gender = gender_raw if gender_raw in ("male", "female") else "male"

    # ── Activity level ────────────────────────────────────────────────────────
    print(f"Activity level options: {', '.join(ACTIVITY_OPTIONS)}")
    # activity_raw = input("Activity level: ").strip().lower().replace(" ", "_")
    activity_raw = "very_active"
    activity_level = activity_raw if activity_raw in ACTIVITY_OPTIONS else "moderate"

    # ── Medical conditions (Phase 2) ──────────────────────────────────────────
    print("\n⚕️  Medical Conditions")
    medical_conditions = _collect_medical_conditions()


    # ── Allergies ─────────────────────────────────────────────────────────────
    # allergies_raw = input("Allergies (comma-separated, or 'none'): ").strip()
    allergies_raw = "none"
    allergies = (
        [a.strip() for a in allergies_raw.split(",")]
        if allergies_raw.lower() != "none"
        else []
    )

    # ── Fitness goal ──────────────────────────────────────────────────────────
    # fitness_goal = input("Fitness goal (e.g., muscle gain, weight loss, maintenance): ").strip()
    fitness_goal = "weight gain"
    while not fitness_goal:
        fitness_goal = input("⚠️ Please specify a fitness goal: ").strip()

    # ── Taste preferences ─────────────────────────────────────────────────────
    # spice_level = input("Preferred spice level (Low / Medium / High): ").strip().capitalize()
    spice_level = "Medium"
    if spice_level not in ("Low", "Medium", "High"):
        print("   ⚠️ Invalid. Defaulting to 'Medium'.")
        spice_level = "Medium"

    # cuisine = input("Preferred cuisine (e.g., Indian, Italian, Chinese): ").strip()
    cuisine = "pakistani"
    if not cuisine:
        cuisine = "Any"

    preferences = {"spice_level": spice_level, "cuisine": cuisine}

    print(f"\n✅ Profile collected for {name}.")
    if medical_conditions:
        print(f"   ⚕️  Conditions: {', '.join(c.condition for c in medical_conditions)}")

    return NutritionState(
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
    )