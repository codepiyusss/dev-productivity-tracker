from datetime import date

from src.database import Database
from src.models.task import Task
from src.streaks import StreakTracker


def tracker_with(*days):
    database = Database(":memory:")
    for day in days:
        database.add_task(Task(
            f"done {day}", completed=True, completed_at=f"{day}T10:00:00"
        ))
    return StreakTracker(database)


def test_no_completions():
    assert tracker_with().longest_streak() == {
        "length": 0, "start": None, "end": None
    }


def test_single_day_is_a_streak_of_one():
    assert tracker_with("2026-11-10").longest_streak() == {
        "length": 1, "start": date(2026, 11, 10), "end": date(2026, 11, 10)
    }


def test_finds_the_longest_run():
    tracker = tracker_with(
        "2026-10-01", "2026-10-02",
        "2026-10-10", "2026-10-11", "2026-10-12", "2026-10-13",
        "2026-11-01", "2026-11-02", "2026-11-03",
    )

    assert tracker.longest_streak() == {
        "length": 4, "start": date(2026, 10, 10), "end": date(2026, 10, 13)
    }


def test_ties_prefer_the_most_recent_run():
    tracker = tracker_with(
        "2026-10-01", "2026-10-02", "2026-10-03",
        "2026-11-05", "2026-11-06", "2026-11-07",
    )

    result = tracker.longest_streak()

    assert result["length"] == 3
    assert result["start"] == date(2026, 11, 5)


def test_run_at_the_very_end_is_counted():
    tracker = tracker_with("2026-11-01", "2026-11-03", "2026-11-04", "2026-11-05")

    assert tracker.longest_streak()["length"] == 3


def test_duplicate_days_do_not_inflate_streak():
    tracker = tracker_with("2026-11-01", "2026-11-01", "2026-11-01")

    assert tracker.longest_streak()["length"] == 1


def test_run_spanning_a_month_boundary():
    tracker = tracker_with("2026-10-30", "2026-10-31", "2026-11-01")

    assert tracker.longest_streak() == {
        "length": 3, "start": date(2026, 10, 30), "end": date(2026, 11, 1)
    }
