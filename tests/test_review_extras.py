from datetime import date, datetime

import pytest

from src.database import Database
from src.models.task import Task
from src.review import build_review
from src.tasks import TaskManager
from src.timetracking import TimeTracker

TODAY = date(2026, 11, 10)
NOW = datetime(2026, 11, 10, 18, 0, 0)


@pytest.fixture
def database():
    return Database(":memory:")


def done(database, title, completed_at):
    database.add_task(Task(title, completed=True, completed_at=completed_at))


def test_time_tracked_in_the_period(database):
    manager = TaskManager(database)
    manager.create_task("Docs", category="work")
    manager.create_task("Book", category="home")
    tracker = TimeTracker(database)
    tracker.log_manual(1, 5400, day=date(2026, 11, 9), now=NOW)
    tracker.log_manual(2, 1800, day=date(2026, 11, 10), now=NOW)
    tracker.log_manual(1, 3600, day=date(2026, 10, 1), now=NOW)      # outside the window

    time_info = build_review(database, 7, TODAY, NOW)["time"]

    assert time_info["total_seconds"] == 7200
    assert [c["category"] for c in time_info["by_category"]] == ["work", "home"]
    assert time_info["by_task"][0]["title"] == "Docs"


def test_time_lists_are_limited_to_three(database):
    manager = TaskManager(database)
    tracker = TimeTracker(database)
    for number in range(5):
        task = manager.create_task(f"T{number}", category=f"c{number}")
        tracker.log_manual(task.task_id, 600 * (number + 1), now=NOW)

    time_info = build_review(database, 7, TODAY, NOW)["time"]

    assert len(time_info["by_task"]) == 3 and len(time_info["by_category"]) == 3


def test_no_daily_goal_means_no_goal_section(database):
    review = build_review(database, 7, TODAY, NOW)

    assert review["daily_goal"] is None and review["weekly_goal"] is None


def test_days_the_daily_goal_was_met(database):
    database.set_goal("daily", 2)
    done(database, "a", "2026-11-10T09:00:00")
    done(database, "b", "2026-11-10T10:00:00")      # 2 on the 10th: met
    done(database, "c", "2026-11-09T09:00:00")      # 1 on the 9th: not met
    done(database, "d", "2026-11-08T09:00:00")
    done(database, "e", "2026-11-08T10:00:00")
    done(database, "f", "2026-11-08T11:00:00")      # 3 on the 8th: met

    goal = build_review(database, 7, TODAY, NOW)["daily_goal"]

    assert goal == {"target": 2, "days_met": 2}


def test_weekly_goal_progress_is_included(database):
    database.set_goal("weekly", 5)
    done(database, "a", "2026-11-10T09:00:00")

    weekly = build_review(database, 7, TODAY, NOW)["weekly_goal"]

    assert weekly["target"] == 5 and weekly["completed"] == 1


def test_journal_days_in_the_period(database):
    entries = [
        {"entry_date": "2026-11-10"}, {"entry_date": "2026-11-08"},
        {"entry_date": "2026-11-08"},           # same day counted once
        {"entry_date": "2026-10-01"},           # too old
    ]

    review = build_review(database, 7, TODAY, NOW, journal_entries=entries)

    assert review["journal_entries"] == 2
    assert build_review(database, 7, TODAY, NOW)["journal_entries"] == 0


def test_overdue_and_streak(database):
    TaskManager(database).create_task("Late", due_date="2026-11-01")
    done(database, "a", "2026-11-10T09:00:00")
    done(database, "b", "2026-11-09T09:00:00")

    review = build_review(database, 7, TODAY, NOW)

    assert review["overdue_count"] == 1
    assert review["streak"] == 2


def test_past_periods_do_not_use_the_real_clock(database):
    old_today = date(2020, 1, 15)
    done(database, "a", "2020-01-15T09:00:00")

    review = build_review(database, 7, old_today)

    assert review["completed_count"] == 1
