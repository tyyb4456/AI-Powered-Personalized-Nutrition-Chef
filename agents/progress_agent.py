"""
agents/progress_agent.py

Reads the user's meal logs and generates a weekly progress report.

Steps:
1. Load meal logs from progress_store (last 7 days)
2. Compute daily adherence percentages
3. Pass adherence data + logs to LLM for pattern detection
4. LLM returns WeeklyProgressReport with insights and recommendations
5. Saves report to state

This agent is called AFTER a week of logging — not in the weekly plan pipeline.
It runs as a standalone check: `python main.py --mode progress`
"""

from __future__ import annotations

from state import NutritionState
from schemas.nutrition_schemas import WeeklyProgressReport
from memory.progress_store import get_logs, get_daily_adherence
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

model = init_chat_model("google_genai:gemini-2.5-flash")
llm   = model.with_structured_output(WeeklyProgressReport)

PROGRESS_PROMPT = ChatPromptTemplate.from_template("""
You are a behavioral nutritionist and progress analyst.

Analyse this user's meal log data and generate an insightful weekly report.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 USER PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Name: {name}
- Fitness Goal: {fitness_goal}
- Daily Calorie Target: {calorie_target} kcal
- Goal type: {goal_type}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 DAILY ADHERENCE (last 7 days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{adherence_table}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🍽️ MEAL LOG DETAIL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{log_detail}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate a WeeklyProgressReport with:

1. week_start and week_end (ISO dates from the log data)
2. avg_adherence_pct: average across all logged days
3. best_day: the day with the highest adherence
4. worst_day: the day with the lowest adherence
5. patterns_identified: 2-4 specific patterns you notice, e.g.:
   - "User consistently skips breakfast on weekdays"
   - "Calorie intake spikes on weekends"
   - "Dinner calories are consistently above target"
6. recommendations: 3-5 specific, actionable recommendations
7. goal_progress: honest assessment of whether they're on track for their goal
8. motivational_note: one encouraging, personalised sentence

Be specific, honest, and empathetic. Not generic.
""")


def _format_adherence_table(adherence_list) -> str:
    if not adherence_list:
        return "No data available for this period."
    lines = ["Date         | Planned | Actual  | Adherence | Logged | Skipped"]
    lines.append("-" * 65)
    for a in adherence_list:
        lines.append(
            f"{a.log_date} | {a.planned_calories:>7} | {a.actual_calories:>7} | "
            f"{a.adherence_pct:>8.1f}% | {a.meals_logged:>6} | {a.meals_skipped:>7}"
        )
    return "\n".join(lines)


def _format_log_detail(logs) -> str:
    if not logs:
        return "No meals logged."
    lines = []
    for log in logs:
        lines.append(
            f"[{log.log_date}] {log.meal_slot:10} | {log.dish_name:35} | "
            f"{log.calories} kcal | P:{log.protein_g:.0f}g C:{log.carbs_g:.0f}g F:{log.fat_g:.0f}g"
        )
    return "\n".join(lines)


def progress_agent_node(state: NutritionState) -> dict:
    print("\n📈 Generating weekly progress report...")

    user_id = state.customer_id or state.name or "default_user"

    # ── Load data from store ──────────────────────────────────────────────────
    logs       = get_logs(user_id, days=7)
    adherence  = get_daily_adherence(user_id, state.calorie_target or 2200, days=7)

    if not logs:
        print("   ⚠️ No meal logs found for this user. Log meals first.")
        return {"pipeline_error": "No meal logs found."}

    print(f"   Found {len(logs)} log entries across {len(adherence)} days")

    adherence_text = _format_adherence_table(adherence)
    log_text       = _format_log_detail(logs)

    messages = PROGRESS_PROMPT.format_messages(
        name=state.name or "User",
        fitness_goal=state.fitness_goal or "general health",
        calorie_target=state.calorie_target or 2200,
        goal_type=state.goal_type or "maintenance",
        adherence_table=adherence_text,
        log_detail=log_text,
    )

    report: WeeklyProgressReport = llm.invoke(messages)

    print(f"✅ Progress report generated")
    print(f"   Avg adherence: {report.avg_adherence_pct:.1f}%")
    print(f"   Best day: {report.best_day} | Worst day: {report.worst_day}")
    print(f"   Goal progress: {report.goal_progress}")
    for pattern in report.patterns_identified:
        print(f"   Pattern: {pattern}")

    return {"progress_report": report}