from datetime import date

from src.analytics import ProductivityAnalytics
from src.database import Database
from src.models.task import Task

TODAY = date(2026, 11, 12)


def analytics_with(*days):
    database = Database(":memory:")
    database.add_task(Task("still pending"))  # keeps the list non-empty
    for day in days:
        database.add_task(Task(
            f"done {day}", completed=True, completed_at=f"{day}T10:00:00"
        ))
    return ProductivityAnalytics(database)


def test_active_streak_is_celebrated():
    insights = analytics_with("2026-11-11", "2026-11-12").get_insights(TODAY)

    assert "You are on a 2-day completion streak." in insights


def test_streak_at_risk_prompts_the_user():
    insights = analytics_with("2026-11-10", "2026-11-11").get_insights(TODAY)

    assert "Complete a task today to keep your 2-day streak alive." in insights


def test_one_day_streak_is_not_mentioned():
    insights = analytics_with("2026-11-12").get_insights(TODAY)

    assert not any("streak" in insight for insight in insights)


def test_no_streak_message_without_completions():
    insights = analytics_with().get_insights(TODAY)

    assert not any("streak" in insight for insight in insights)
