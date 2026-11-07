from datetime import date

from src.analytics import ProductivityAnalytics
from src.database import Database
from src.models.task import Task

TODAY = date(2026, 11, 12)


def test_streak_uses_completion_date_not_creation_date():
    database = Database(":memory:")
    # Created long ago, but finished today and yesterday.
    for day in ("2026-11-11", "2026-11-12"):
        database.add_task(Task(
            "old task", completed=True,
            created_at="2026-10-01T09:00:00", completed_at=f"{day}T10:00:00"
        ))

    assert ProductivityAnalytics(database).get_completion_streak(TODAY) == 2


def test_tasks_created_today_but_not_completed_do_not_count():
    database = Database(":memory:")
    database.add_task(Task("pending", created_at="2026-11-12T09:00:00"))

    assert ProductivityAnalytics(database).get_completion_streak(TODAY) == 0


def test_legacy_completed_tasks_without_timestamp_do_not_count():
    database = Database(":memory:")
    database.add_task(Task(
        "legacy", completed=True, created_at="2026-11-12T09:00:00"
    ))

    assert ProductivityAnalytics(database).get_completion_streak(TODAY) == 0


def test_streak_is_alive_if_last_completion_was_yesterday():
    database = Database(":memory:")
    database.add_task(Task(
        "done", completed=True, completed_at="2026-11-11T10:00:00"
    ))

    assert ProductivityAnalytics(database).get_completion_streak(TODAY) == 1
