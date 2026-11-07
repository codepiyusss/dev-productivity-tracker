from datetime import date

from src.database import Database
from src.models.task import Task
from src.streaks import StreakTracker


def add_done(database, title, completed_at):
    database.add_task(Task(title, completed=True, completed_at=completed_at))


def test_no_tasks_means_no_dates():
    tracker = StreakTracker(Database(":memory:"))

    assert tracker.get_daily_counts() == {}
    assert tracker.get_completion_dates() == []


def test_daily_counts_group_tasks_by_completion_day():
    database = Database(":memory:")
    add_done(database, "a", "2026-11-10T08:00:00")
    add_done(database, "b", "2026-11-10T22:15:00")
    add_done(database, "c", "2026-11-11T07:00:00")

    counts = StreakTracker(database).get_daily_counts()

    assert counts == {date(2026, 11, 10): 2, date(2026, 11, 11): 1}


def test_completion_dates_are_sorted_and_unique():
    database = Database(":memory:")
    add_done(database, "late", "2026-11-12T08:00:00")
    add_done(database, "early", "2026-11-09T08:00:00")
    add_done(database, "early again", "2026-11-09T18:00:00")

    dates = StreakTracker(database).get_completion_dates()

    assert dates == [date(2026, 11, 9), date(2026, 11, 12)]


def test_pending_legacy_and_invalid_tasks_are_ignored():
    database = Database(":memory:")
    database.add_task(Task("pending"))
    database.add_task(Task("legacy", completed=True))  # no timestamp
    add_done(database, "garbled", "yesterday-ish")
    add_done(database, "good", "2026-11-10T09:00:00")

    counts = StreakTracker(database).get_daily_counts()

    assert counts == {date(2026, 11, 10): 1}


def test_creation_date_is_not_used():
    database = Database(":memory:")
    database.add_task(Task(
        "made early", completed=True,
        created_at="2026-11-01T09:00:00", completed_at="2026-11-10T09:00:00"
    ))

    assert StreakTracker(database).get_completion_dates() == [date(2026, 11, 10)]
