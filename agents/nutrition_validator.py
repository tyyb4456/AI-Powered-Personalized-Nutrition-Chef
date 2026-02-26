"""
agents/nutrition_validator.py

Validates whether the generated recipe actually meets the user's targets.

Key changes from original:
- Uses structured NutritionFacts from RecipeOutput (not a fake estimated value)
- Multi-dimensional: checks calories AND each macro ratio
- Produces a rich ValidationResult with per-check details
- Returns only keys this agent modifies
"""

from state import NutritionState
from schemas.nutrition_schemas import ValidationResult


# ── Tolerance thresholds ──────────────────────────────────────────────────────
CALORIE_TOLERANCE_PCT = 10.0   # ±10% of calorie target is acceptable
MACRO_TOLERANCE_PCT   = 5.0    # ±5% of each macro ratio is acceptable
MAX_RETRIES           = 2      # how many macro adjustment loops before giving up


def _actual_macro_pcts(nutrition) -> dict:
    """
    Calculate actual macro percentages from gram values.
    Protein & Carbs: 4 kcal/g | Fat: 9 kcal/g
    """
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


def nutrition_validation_agent_node(state: NutritionState) -> dict:
    print("\n✅ Validating nutritional alignment...")

    # ── Determine which recipe to validate ───────────────────────────────────
    # After macro adjustment the adjusted recipe is stored in macro_adjustment_output
    if state.adjusted_by_macro_agent and state.macro_adjustment_output:
        recipe = state.macro_adjustment_output.adjusted_recipe
        print("   Validating macro-adjusted recipe...")
    else:
        recipe = state.generated_recipe
        print("   Validating original generated recipe...")

    if recipe is None:
        # Should never happen — pipeline guards against this
        return {
            "validation_passed": False,
            "validation_notes":  "❌ No recipe found to validate.",
            "validation_result": None,
        }

    nutrition = recipe.nutrition
    target_cal = state.calorie_target
    target_macro = state.macro_split

    # ── 1. Calorie check ─────────────────────────────────────────────────────
    calorie_diff_pct = abs(nutrition.calories - target_cal) / target_cal * 100
    calorie_ok = calorie_diff_pct <= CALORIE_TOLERANCE_PCT

    # ── 2. Macro ratio checks ─────────────────────────────────────────────────
    actual_macros = _actual_macro_pcts(nutrition)

    protein_diff = abs(actual_macros["protein"] - target_macro.protein)
    carbs_diff   = abs(actual_macros["carbs"]   - target_macro.carbs)
    fat_diff     = abs(actual_macros["fat"]      - target_macro.fat)

    protein_ok = protein_diff <= MACRO_TOLERANCE_PCT
    carbs_ok   = carbs_diff   <= MACRO_TOLERANCE_PCT
    fat_ok     = fat_diff     <= MACRO_TOLERANCE_PCT

    overall_pass = calorie_ok and protein_ok and carbs_ok and fat_ok

    # ── Build notes ───────────────────────────────────────────────────────────
    lines = [
        f"Calorie check: {'✅' if calorie_ok else '❌'} "
        f"{nutrition.calories} kcal vs target {target_cal} kcal "
        f"({calorie_diff_pct:.1f}% diff)",

        f"Protein:  {'✅' if protein_ok else '❌'} "
        f"actual {actual_macros['protein']}% vs target {target_macro.protein}% "
        f"(diff {protein_diff:.1f}%)",

        f"Carbs:    {'✅' if carbs_ok else '❌'} "
        f"actual {actual_macros['carbs']}% vs target {target_macro.carbs}% "
        f"(diff {carbs_diff:.1f}%)",

        f"Fat:      {'✅' if fat_ok else '❌'} "
        f"actual {actual_macros['fat']}% vs target {target_macro.fat}% "
        f"(diff {fat_diff:.1f}%)",
    ]
    notes = "\n".join(lines)

    result = ValidationResult(
        passed=overall_pass,
        calorie_check=calorie_ok,
        protein_check=protein_ok,
        carbs_check=carbs_ok,
        fat_check=fat_ok,
        notes=notes,
        calorie_diff_pct=round(calorie_diff_pct, 2),
    )

    if overall_pass:
        print(f"   ✅ Validation passed.")
    else:
        print(f"   ❌ Validation failed (retry {state.retry_count}/{MAX_RETRIES}):")

    print(f"\n{notes}\n")

    return {
        "validation_result":  result,
        "validation_passed":  overall_pass,
        "validation_notes":   notes,
    }