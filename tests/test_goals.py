from datetime import date

import pytest

from src.database import Database
from src.goals import GoalTracker
from src.models.task import Task

TODAY = date(2026, 11, 11)  # Wednesday; its week is Nov 9 - Nov 15


@pytest.fixture
def database():
    return Database(":memory:")


@pytest.fixture
def tracker(database):
    return GoalTracker(database)


def done(database, title, completed_at):
    database.add_task(Task(title, completed=True, completed_at=completed_at))


def test_progress_is_none_without_goal(tracker):
    assert tracker.get_progress("daily", TODAY) is None
    assert tracker.get_all_progress(TODAY) == []


def test_daily_progress_counts_only_today(tracker, database):
    tracker.set_goal("daily", 3)
    done(database, "today 1", "2026-11-11T08:00:00")
    done(database, "today 2", "2026-11-11T21:30:00")
    done(database, "yesterday", "2026-11-10T12:00:00")

    progress = tracker.get_progress("daily", TODAY)

    assert progress["completed"] == 2
    assert progress["remaining"] == 1
    assert progress["percent"] == 66.7
    assert progress["met"] is False


def test_weekly_progress_covers_monday_to_sunday(tracker, database):
    tracker.set_goal("weekly", 4)
    done(database, "monday", "2026-11-09T00:00:00")
    done(database, "sunday", "2026-11-15T23:59:59")
    done(database, "last sunday", "2026-11-08T23:59:59")
    done(database, "next monday", "2026-11-16T00:00:00")

    progress = tracker.get_progress("weekly", TODAY)

    assert progress["completed"] == 2
    assert (progress["start"], progress["end"]) == ("2026-11-09", "2026-11-15")


def test_goal_met_and_percent_capped_at_100(tracker, database):
    tracker.set_goal("daily", 1)
    done(database, "a", "2026-11-11T08:00:00")
    done(database, "b", "2026-11-11T09:00:00")

    progress = tracker.get_progress("daily", TODAY)

    assert progress["met"] is True
    assert progress["completed"] == 2
    assert progress["remaining"] == 0
    assert progress["percent"] == 100


def test_pending_and_legacy_tasks_are_not_counted(tracker, database):
    tracker.set_goal("daily", 2)
    database.add_task(Task("pending"))
    database.add_task(Task("legacy done", completed=True))  # no timestamp
    done(database, "bad stamp", "not-a-date")

    assert tracker.get_progress("daily", TODAY)["completed"] == 0


def test_reopened_task_no_longer_counts(tracker, database):
    tracker.set_goal("daily", 1)
    done(database, "a", "2026-11-11T08:00:00")
    task = database.get_all_tasks()[0]
    task.mark_pending()
    database.update_task(task)

    assert tracker.get_progress("daily", TODAY)["completed"] == 0


def test_get_all_progress_lists_daily_then_weekly(tracker):
    tracker.set_goal("weekly", 10)
    tracker.set_goal("daily", 2)

    periods = [p["period"] for p in tracker.get_all_progress(TODAY)]

    assert periods == ["daily", "weekly"]


@pytest.mark.parametrize("period", ["monthly", "", "year"])
def test_invalid_period_is_rejected(tracker, period):
    with pytest.raises(ValueError):
        tracker.set_goal(period, 3)


@pytest.mark.parametrize("target", [0, -1, 1001, 2.5, "3", True])
def test_invalid_target_is_rejected(tracker, target):
    with pytest.raises(ValueError):
        tracker.set_goal("daily", target)


def test_period_is_case_insensitive_and_clearable(tracker, database):
    tracker.set_goal("DAILY", 3)

    assert database.get_goal("daily") == 3
    assert tracker.clear_goal(" Daily ") is True
    assert tracker.clear_goal("daily") is False
