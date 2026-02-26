"""
agents/meal_prep_agent.py

Analyses the meal plan and generates an optimised prep schedule.

Logic:
1. Scan all recipes for batch-cookable components
   (grains, proteins, sauces, marinated items)
2. Group by prep day (Sunday for M–W meals, Wednesday for Th–Sa)
3. Generate PrepTask list with duration + storage instructions
4. Sum total prep time and identify which 2 days need prep
"""

from state import WeeklyPlanState
from schemas.nutrition_schemas import MealPrepSchedule
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")
llm   = model.with_structured_output(MealPrepSchedule)

PREP_PROMPT = ChatPromptTemplate.from_template("""
You are a professional meal prep consultant.

Analyse the 7-day meal plan below and create an optimised prep schedule
that minimises daily cooking time through smart batch preparation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 MEAL PLAN OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{meal_plan_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Identify components that can be BATCH-COOKED (appear in 2+ meals):
   - Grains (rice, oats, quinoa)
   - Proteins (grilled chicken, boiled eggs, cooked lentils)
   - Bases (tomato sauce, curry base, marinade)
   - Vegetables (roasted, steamed, or blanched)

2. Create prep tasks split across 2 prep days:
   - Sunday prep: covers Monday, Tuesday, Wednesday meals
   - Wednesday prep: covers Thursday, Friday, Saturday, Sunday meals

3. For each PrepTask:
   - Specific task description (quantities + method)
   - Which meals it covers (by dish name)
   - Duration in minutes
   - Storage instruction (container type, days in fridge/freezer)
   - Reheating tip

4. efficiency_notes: overall time savings vs cooking from scratch daily

Fitness goal: {fitness_goal}
""")


def _build_meal_plan_summary(state: WeeklyPlanState) -> str:
    """Build a compact text summary of the meal plan for the prompt."""
    lines = []
    for day_plan in state.meal_plan.days:
        meals_text = " | ".join(
            f"{ms.slot}: {ms.recipe.dish_name} ({ms.recipe.nutrition.calories} kcal)"
            for ms in day_plan.meals
        )
        lines.append(f"{day_plan.day}: {meals_text}")
    return "\n".join(lines)


def meal_prep_agent_node(state: WeeklyPlanState) -> dict:
    print("\n🥘 Generating meal prep schedule...")

    if not state.meal_plan:
        return {"pipeline_error": "MealPrepAgent: no meal_plan in state."}

    summary = _build_meal_plan_summary(state)

    messages = PREP_PROMPT.format_messages(
        meal_plan_summary=summary,
        fitness_goal=state.fitness_goal or "general health",
    )

    schedule: MealPrepSchedule = llm.invoke(messages)

    print(f"✅ Prep schedule: {len(schedule.tasks)} tasks")
    print(f"   Total prep time: {schedule.total_prep_time_min} minutes across {schedule.prep_days}")
    for task in schedule.tasks:
        print(f"   [{task.prep_day}] {task.task} ({task.duration_minutes} min)")
        print(f"         Storage: {task.storage_instruction}")

    return {
        "prep_schedule":   schedule,
        "prep_generated":  True,
    }