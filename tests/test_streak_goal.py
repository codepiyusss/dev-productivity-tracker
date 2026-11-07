from datetime import date

from src.database import Database
from src.models.task import Task
from src.streaks import StreakTracker

TODAY = date(2026, 11, 12)


def build(daily_target, completions):
    """completions: {'2026-11-12': 2, ...} -> tasks completed per day."""
    database = Database(":memory:")
    if daily_target:
        database.set_goal("daily", daily_target)

    for day, count in completions.items():
        for number in range(count):
            database.add_task(Task(
                f"{day}-{number}", completed=True,
                completed_at=f"{day}T1{number}:00:00"
            ))

    return StreakTracker(database)


def test_no_daily_goal_returns_none():
    assert build(None, {"2026-11-12": 3}).goal_streak(TODAY) is None


def test_weekly_goal_alone_does_not_create_a_daily_streak():
    database = Database(":memory:")
    database.set_goal("weekly", 5)

    assert StreakTracker(database).goal_streak(TODAY) is None


def test_counts_only_days_that_met_the_target():
    tracker = build(2, {
        "2026-11-10": 2, "2026-11-11": 3, "2026-11-12": 2,
    })

    streak = tracker.goal_streak(TODAY)

    assert streak["length"] == 3
    assert streak["target"] == 2
    assert streak["active_today"] is True


def test_day_below_target_breaks_the_goal_streak():
    tracker = build(2, {
        "2026-11-09": 2, "2026-11-10": 1, "2026-11-11": 2, "2026-11-12": 2,
    })

    assert tracker.goal_streak(TODAY)["length"] == 2


def test_goal_streak_has_end_of_day_grace():
    tracker = build(2, {"2026-11-10": 2, "2026-11-11": 2, "2026-11-12": 1})

    streak = tracker.goal_streak(TODAY)

    assert streak["length"] == 2
    assert streak["active_today"] is False


def test_goal_streak_is_zero_when_nothing_meets_target():
    streak = build(3, {"2026-11-12": 2, "2026-11-11": 1}).goal_streak(TODAY)

    assert streak["length"] == 0


def test_plain_streak_is_unaffected_by_goal():
    tracker = build(5, {"2026-11-11": 1, "2026-11-12": 1})

    assert tracker.current_streak(TODAY)["length"] == 2
    assert tracker.goal_streak(TODAY)["length"] == 0
