"""
agents/nutrition_validator.py

Phase 2 upgrades:
- Fiber adequacy check (5g minimum for adults, 8g for seniors)
- Allergen double-check: scans final ingredient list against state.allergies
- Age/medical condition checks: sodium limit for hypertension/seniors
- All checks feed into ValidationResult with new fiber_check + allergen_check fields
- Returns only keys this agent modifies
"""

from state import NutritionState
from schemas.nutrition_schemas import ValidationResult


# ── Tolerance thresholds ──────────────────────────────────────────────────────
CALORIE_TOLERANCE_PCT  = 10.0   # ±10% of calorie target
MACRO_TOLERANCE_PCT    = 5.0    # ±5% per macro ratio
MIN_FIBER_G_DEFAULT    = 5.0    # minimum fiber for adults
MIN_FIBER_G_SENIOR     = 8.0    # higher fiber goal for seniors
MAX_SODIUM_SENIOR_MG   = 600.0  # sodium cap for seniors / hypertension
MAX_RETRIES            = 2


def _actual_macro_pcts(nutrition) -> dict:
    total_kcal = (
        nutrition.protein_g * 4
        + nutrition.carbs_g * 4
        + nutrition.fat_g * 9
    )
    if total_kcal == 0:
        return {"protein": 0, "carbs": 0, "fat": 0}
    return {
        "protein": round((nutrition.protein_g * 4 / total_kcal) * 100, 1),
        "carbs":   round((nutrition.carbs_g   * 4 / total_kcal) * 100, 1),
        "fat":     round((nutrition.fat_g     * 9 / total_kcal) * 100, 1),
    }


def _check_allergens_in_recipe(recipe, allergies: list[str]) -> tuple[bool, list[str]]:
    """
    Scan all ingredient names for allergen keywords.
    Returns (is_safe, list_of_flagged_ingredients).
    """
    if not allergies:
        return True, []

    flagged = []
    for ing in recipe.ingredients:
        ing_lower = ing.name.lower()
        for allergen in allergies:
            if allergen.lower() in ing_lower:
                flagged.append(f"{ing.name} (contains: {allergen})")

    return len(flagged) == 0, flagged


def nutrition_validation_agent_node(state: NutritionState) -> dict:
    print("\n✅ Validating nutritional alignment...")

    # ── Determine which recipe to validate ───────────────────────────────────
    if state.adjusted_by_macro_agent and state.macro_adjustment_output:
        recipe = state.macro_adjustment_output.adjusted_recipe
        print("   Validating macro-adjusted recipe...")
    else:
        recipe = state.generated_recipe
        print("   Validating original generated recipe...")

    if recipe is None:
        return {
            "validation_passed": False,
            "validation_notes":  "❌ No recipe found to validate.",
            "validation_result": None,
        }

    nutrition     = recipe.nutrition
    target_cal    = state.calorie_target
    target_macro  = state.macro_split
    age_profile   = state.age_profile
    conditions    = state.medical_conditions or []
    condition_names = [c.condition for c in conditions]

    # ── 1. Calorie check ─────────────────────────────────────────────────────
    calorie_diff_pct = abs(nutrition.calories - target_cal) / target_cal * 100
    calorie_ok       = calorie_diff_pct <= CALORIE_TOLERANCE_PCT

    # ── 2. Macro ratio checks ─────────────────────────────────────────────────
    actual = _actual_macro_pcts(nutrition)

    protein_diff = abs(actual["protein"] - target_macro.protein)
    carbs_diff   = abs(actual["carbs"]   - target_macro.carbs)
    fat_diff     = abs(actual["fat"]     - target_macro.fat)

    protein_ok = protein_diff <= MACRO_TOLERANCE_PCT
    carbs_ok   = carbs_diff   <= MACRO_TOLERANCE_PCT
    fat_ok     = fat_diff     <= MACRO_TOLERANCE_PCT

    # ── 3. Fiber check ────────────────────────────────────────────────────────
    is_senior   = age_profile and age_profile.age_group == "senior"
    min_fiber   = MIN_FIBER_G_SENIOR if is_senior else MIN_FIBER_G_DEFAULT
    fiber_g     = nutrition.fiber_g
    fiber_ok    = (fiber_g is not None and fiber_g >= min_fiber)
    fiber_label = f"{fiber_g:.1f}g" if fiber_g is not None else "not reported"

    # ── 4. Allergen double-check ──────────────────────────────────────────────
    allergen_safe, flagged_allergens = _check_allergens_in_recipe(recipe, state.allergies)

    # ── 5. Sodium check (seniors + hypertension + heart disease) ─────────────
    sodium_check_required = (
        is_senior
        or "hypertension" in condition_names
        or "heart_disease" in condition_names
    )
    sodium_ok    = True
    sodium_label = "not checked"
    if sodium_check_required and nutrition.sodium_mg is not None:
        sodium_ok    = nutrition.sodium_mg <= MAX_SODIUM_SENIOR_MG
        sodium_label = f"{nutrition.sodium_mg:.0f}mg (limit: {MAX_SODIUM_SENIOR_MG:.0f}mg)"
    elif sodium_check_required:
        sodium_label = "⚠️ sodium not reported — cannot verify"

    # ── Overall pass ──────────────────────────────────────────────────────────
    overall_pass = (
        calorie_ok and protein_ok and carbs_ok and fat_ok
        and fiber_ok and allergen_safe
        and (sodium_ok if sodium_check_required and nutrition.sodium_mg else True)
    )

    # ── Build notes ───────────────────────────────────────────────────────────
    lines = [
        f"Calorie:  {'✅' if calorie_ok else '❌'} "
        f"{nutrition.calories} kcal vs target {target_cal} kcal "
        f"({calorie_diff_pct:.1f}% diff)",

        f"Protein:  {'✅' if protein_ok else '❌'} "
        f"actual {actual['protein']}% vs target {target_macro.protein}% "
        f"(diff {protein_diff:.1f}%)",

        f"Carbs:    {'✅' if carbs_ok else '❌'} "
        f"actual {actual['carbs']}% vs target {target_macro.carbs}% "
        f"(diff {carbs_diff:.1f}%)",

        f"Fat:      {'✅' if fat_ok else '❌'} "
        f"actual {actual['fat']}% vs target {target_macro.fat}% "
        f"(diff {fat_diff:.1f}%)",

        f"Fiber:    {'✅' if fiber_ok else '❌'} "
        f"{fiber_label} (min: {min_fiber}g)",

        f"Allergens: {'✅ Clear' if allergen_safe else '❌ FLAGGED: ' + ', '.join(flagged_allergens)}",
    ]

    if sodium_check_required:
        lines.append(f"Sodium:   {'✅' if sodium_ok else '❌'} {sodium_label}")

    notes = "\n".join(lines)

    result = ValidationResult(
        passed=overall_pass,
        calorie_check=calorie_ok,
        protein_check=protein_ok,
        carbs_check=carbs_ok,
        fat_check=fat_ok,
        fiber_check=fiber_ok,
        allergen_check=allergen_safe,
        notes=notes,
        calorie_diff_pct=round(calorie_diff_pct, 2),
    )

    status = "✅ Validation passed." if overall_pass else f"❌ Validation failed (retry {state.retry_count}/{MAX_RETRIES})"
    print(f"   {status}")
    print(f"\n{notes}\n")

    return {
        "validation_result": result,
        "validation_passed": overall_pass,
        "validation_notes":  notes,
    }