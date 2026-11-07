from datetime import date

import pytest

from src.database import Database
from src.models.task import Task
from src.streaks import StreakTracker

TODAY = date(2026, 11, 12)


def tracker_with(*days):
    database = Database(":memory:")
    for day in days:
        database.add_task(Task(
            f"done {day}", completed=True, completed_at=f"{day}T10:00:00"
        ))
    return StreakTracker(database)


def test_no_completions_gives_zero_streak():
    streak = tracker_with().current_streak(TODAY)

    assert streak == {"length": 0, "active_today": False, "last_active": None}


def test_streak_counts_consecutive_days_through_today():
    tracker = tracker_with("2026-11-10", "2026-11-11", "2026-11-12")

    streak = tracker.current_streak(TODAY)

    assert streak["length"] == 3
    assert streak["active_today"] is True
    assert streak["last_active"] == TODAY


def test_streak_survives_until_end_of_today():
    tracker = tracker_with("2026-11-09", "2026-11-10", "2026-11-11")

    streak = tracker.current_streak(TODAY)

    assert streak["length"] == 3
    assert streak["active_today"] is False
    assert streak["last_active"] == date(2026, 11, 11)


def test_streak_breaks_after_a_missed_day():
    tracker = tracker_with("2026-11-08", "2026-11-09", "2026-11-10")

    streak = tracker.current_streak(TODAY)

    assert streak["length"] == 0
    assert streak["last_active"] == date(2026, 11, 10)


def test_gap_in_the_middle_ends_the_run():
    tracker = tracker_with("2026-11-08", "2026-11-10", "2026-11-11", "2026-11-12")

    assert tracker.current_streak(TODAY)["length"] == 3


def test_several_tasks_on_one_day_count_as_one_day():
    tracker = tracker_with("2026-11-12", "2026-11-12", "2026-11-11")

    assert tracker.current_streak(TODAY)["length"] == 2


def test_future_completions_are_not_counted_as_last_active():
    tracker = tracker_with("2026-11-20")

    streak = tracker.current_streak(TODAY)

    assert streak["length"] == 0
    assert streak["last_active"] is None


@pytest.mark.parametrize("length", [1, 7, 30])
def test_long_runs(length):
    from datetime import timedelta
    days = [(TODAY - timedelta(days=i)).isoformat() for i in range(length)]

    assert tracker_with(*days).current_streak(TODAY)["length"] == length
