"""
agents/recipe_agent.py — Phase 4

Phase 4 upgrades:
- Checks Redis cache before calling the LLM (saves API cost on repeated requests)
- Saves generated recipe to PostgreSQL via RecipeRepository
- Stores recipe_id in state so feedback_agent can link feedback to the recipe
- All Phase 3 RAG + medical/age logic preserved
"""

from __future__ import annotations

import logging

from state import NutritionState
from schemas.nutrition_schemas import RecipeOutput
from memory.recipe_context_store import retrieve_context
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

model = init_chat_model("google_genai:gemini-2.5-flash")
llm   = model.with_structured_output(RecipeOutput)

RECIPE_PROMPT = ChatPromptTemplate.from_template("""
You are a world-class AI chef and certified nutritionist.

Create a personalized, health-optimized meal for this customer.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 CUSTOMER PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Age: {age} ({age_group})
- Gender: {gender}
- Fitness Goal: {fitness_goal}
- Calorie Target: {calorie_target} kcal
- Macro Split — Protein: {protein_pct}% | Carbs: {carbs_pct}% | Fat: {fat_pct}%
- Cuisine Preference: {cuisine}
- Spice Level: {spice_level}
- Allergies / Restrictions: {allergies}
- Medical Conditions: {medical_conditions}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚕️ AGE & MEDICAL DIETARY NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{age_notes}
{medical_notes}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 LEARNED PREFERENCES (from past sessions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{learned_preferences_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 REFERENCE EXAMPLES (use as inspiration, not copies)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{recipe_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Total calories within ±10% of {calorie_target} kcal
2. Macro ratios within ±5% of targets above
3. ZERO allergens — absolutely no exceptions
4. Match the cuisine and spice preference
5. Respect ALL age and medical notes above
6. Include fiber-rich ingredients (aim for 5–8g fiber minimum)
7. Accessible ingredients, realistic home cook steps
8. If learned preferences exist, honour liked/disliked ingredients

Return a complete recipe: dish name, ingredients with quantities,
numbered steps, and full nutritional breakdown including fiber.
""")


# ── Prompt-building helpers (unchanged from Phase 3) ─────────────────────────

def _format_recipe_context(contexts) -> str:
    if not contexts:
        return "No specific examples available — use your best culinary judgment."
    lines = []
    for i, ctx in enumerate(contexts, 1):
        lines.append(
            f"Example {i}: {ctx.dish_name} ({ctx.cuisine}) — ~{ctx.approx_calories} kcal\n"
            f"  Proteins: {', '.join(ctx.key_proteins)}\n"
            f"  Note: {ctx.notes}"
        )
    return "\n\n".join(lines)


def _format_medical_notes(conditions) -> str:
    if not conditions:
        return "No medical conditions."
    condition_map = {
        "diabetes":            "⚠️ Diabetic: use low-GI carbs, avoid refined sugar.",
        "hypertension":        "⚠️ Hypertension: keep sodium BELOW 600mg per meal.",
        "celiac":              "⚠️ Celiac: absolutely NO gluten.",
        "lactose_intolerance": "⚠️ Lactose intolerant: no dairy. Use plant-based alternatives.",
        "kidney_disease":      "⚠️ Kidney disease: limit protein, reduce phosphorus.",
        "heart_disease":       "⚠️ Heart disease: low saturated fat, low sodium.",
        "ibs":                 "⚠️ IBS: avoid high-FODMAP foods.",
        "anemia":              "⚠️ Anemia: include iron-rich foods.",
        "osteoporosis":        "⚠️ Osteoporosis: include calcium-rich foods.",
    }
    notes = [condition_map[c.condition] for c in conditions if c.condition in condition_map]
    return "\n".join(notes) if notes else "No specific medical dietary restrictions."


def _format_learned_preferences(lp) -> str:
    if lp is None:
        return "No previous session data available."
    lines = []
    if lp.liked_ingredients:     lines.append(f"✅ Likes: {', '.join(lp.liked_ingredients)}")
    if lp.disliked_ingredients:  lines.append(f"❌ Dislikes: {', '.join(lp.disliked_ingredients)}")
    if lp.preferred_textures:    lines.append(f"🍴 Textures: {', '.join(lp.preferred_textures)}")
    if lp.spice_preference:      lines.append(f"🌶️ Spice: {lp.spice_preference}")
    if lp.session_insights:      lines.append(f"💡 Notes: {'; '.join(lp.session_insights)}")
    return "\n".join(lines) if lines else "No specific preferences learned yet."


# ── Agent Node ────────────────────────────────────────────────────────────────

def recipe_generator_node(state: NutritionState) -> dict:
    print("\n🍽️ Generating personalized recipe...")

    macro     = state.macro_split
    cuisine   = state.preferences.get("cuisine", "any")
    goal_type = state.goal_type or "maintenance"
    user_id   = state.customer_id or state.name or "anonymous"

    # ── 1. Check Redis cache ──────────────────────────────────────────────────
    try:
        from cache.redis_client import redis_client
        allowed, count = redis_client.check_rate_limit(user_id)
        if not allowed:
            print(f"   ⚠️ Rate limit reached ({count} calls this hour). Using cached or default recipe.")

        cached = redis_client.get_cached_recipe(
            user_id=user_id,
            goal_type=goal_type,
            calorie_target=state.calorie_target,
            cuisine=cuisine,
            allergies=state.allergies,
        )
        if cached:
            print("   ⚡ Cache HIT — returning cached recipe.")
            recipe = RecipeOutput(**cached)
            return {
                "generated_recipe": recipe,
                "recipe_generated": True,
                "recipe_context":   [],
            }
    except Exception as e:
        logger.warning("Redis check failed (%s). Proceeding without cache.", e)

    # ── 2. Retrieve RAG context ───────────────────────────────────────────────
    contexts = retrieve_context(goal_type=goal_type, cuisine=cuisine, n=2)
    print(f"   📚 Injecting {len(contexts)} reference recipe(s) as context")

    # ── 3. Build prompt ───────────────────────────────────────────────────────
    age_profile   = state.age_profile
    age_group     = age_profile.age_group if age_profile else "adult"
    age_notes     = age_profile.notes     if age_profile else "Standard adult guidelines."
    conditions_str = ", ".join(c.condition for c in state.medical_conditions) if state.medical_conditions else "none"

    messages = RECIPE_PROMPT.format_messages(
        age=state.age or "not specified",
        age_group=age_group,
        gender=state.gender or "not specified",
        fitness_goal=state.fitness_goal or "maintenance",
        calorie_target=state.calorie_target,
        protein_pct=macro.protein,
        carbs_pct=macro.carbs,
        fat_pct=macro.fat,
        cuisine=cuisine,
        spice_level=state.preferences.get("spice_level", "medium"),
        allergies=", ".join(state.allergies) if state.allergies else "none",
        medical_conditions=conditions_str,
        age_notes=age_notes,
        medical_notes=_format_medical_notes(state.medical_conditions),
        learned_preferences_text=_format_learned_preferences(state.learned_preferences),
        recipe_context=_format_recipe_context(contexts),
    )

    # ── 4. LLM call ───────────────────────────────────────────────────────────
    recipe: RecipeOutput = llm.invoke(messages)

    print(f"✅ Recipe generated: '{recipe.dish_name}'")
    print(f"   {recipe.nutrition.calories} kcal | "
          f"P:{recipe.nutrition.protein_g}g C:{recipe.nutrition.carbs_g}g F:{recipe.nutrition.fat_g}g")

    # ── 5. Save to PostgreSQL ──────────────────────────────────────────────────
    saved_recipe_id: str | None = None
    try:
        from db.database import get_db
        from db.repositories import RecipeRepository
        with get_db() as db:
            saved_recipe_id = RecipeRepository(db).save(recipe, source="generated")
        print(f"   💾 Recipe saved to DB (id: {saved_recipe_id[:8]}...)")
    except Exception as e:
        logger.warning("Could not save recipe to DB (%s).", e)

    # ── 6. Cache in Redis for 24h ─────────────────────────────────────────────
    try:
        from cache.redis_client import redis_client
        redis_client.cache_recipe(
            recipe_dict=recipe.model_dump(),
            user_id=user_id,
            goal_type=goal_type,
            calorie_target=state.calorie_target,
            cuisine=cuisine,
            allergies=state.allergies,
        )
    except Exception as e:
        logger.warning("Could not cache recipe in Redis (%s).", e)

    return {
        "generated_recipe":  recipe,
        "recipe_generated":  True,
        "recipe_context":    contexts,
        "current_recipe_id": saved_recipe_id,  # passed to feedback_agent
    }