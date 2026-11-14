from datetime import date, datetime

import pytest

from src.database import Database
from src.dependencies import DependencyManager
from src.models.task import Task
from src.tasks import TaskManager
from src.timetracking import TimeTracker
from src.today import build_today_summary

TODAY = date(2026, 11, 10)
NOW = datetime(2026, 11, 10, 10, 0, 0)


@pytest.fixture
def setup():
    database = Database(":memory:")
    return database, TaskManager(database)


def titles(tasks):
    return [t.title for t in tasks]


def test_empty_database(setup):
    database, _ = setup

    summary = build_today_summary(database, TODAY, NOW)

    assert summary["overdue"] == summary["due_today"] == summary["upcoming"] == []
    assert summary["pending_count"] == 0
    assert summary["timer"] is None
    assert summary["goals"] == []
    assert summary["streak"]["length"] == 0
    assert summary["done_today"] == 0


def test_tasks_are_sorted_into_overdue_today_and_upcoming(setup):
    database, manager = setup
    manager.create_task("Late", due_date="2026-11-01")
    manager.create_task("Later", due_date="2026-11-08")
    manager.create_task("Today", due_date="2026-11-10")
    manager.create_task("Tomorrow", due_date="2026-11-11")
    manager.create_task("In 3 days", due_date="2026-11-13")
    manager.create_task("In 4 days", due_date="2026-11-14")
    manager.create_task("No date")

    summary = build_today_summary(database, TODAY, NOW)

    assert titles(summary["overdue"]) == ["Late", "Later"]
    assert titles(summary["due_today"]) == ["Today"]
    assert titles(summary["upcoming"]) == ["Tomorrow", "In 3 days"]
    assert summary["pending_count"] == 7


def test_completed_tasks_are_excluded(setup):
    database, manager = setup
    task = manager.create_task("Done already", due_date="2026-11-01")
    manager.complete_task(task.task_id)

    assert build_today_summary(database, TODAY, NOW)["overdue"] == []


def test_unreadable_due_dates_are_ignored(setup):
    database, _ = setup
    database.add_task(Task("Legacy", due_date="31-12-2026"))

    summary = build_today_summary(database, TODAY, NOW)

    assert summary["overdue"] == summary["due_today"] == summary["upcoming"] == []
    assert summary["pending_count"] == 1


def test_ready_and_blocked_counts(setup):
    database, manager = setup
    for title in ("A", "B", "C"):
        manager.create_task(title)
    DependencyManager(database).add(2, 1)

    summary = build_today_summary(database, TODAY, NOW)

    assert (summary["ready_count"], summary["blocked_count"]) == (2, 1)


def test_running_timer_goals_streak_and_done_today(setup):
    database, manager = setup
    task = manager.create_task("Write docs")
    other = manager.create_task("Other")
    database.set_goal("daily", 2)
    TimeTracker(database).start(task.task_id, datetime(2026, 11, 10, 9, 30, 0))
    done = database.get_task(other.task_id)
    done.mark_completed()
    done.completed_at = "2026-11-10T08:00:00"
    database.update_task(done)

    summary = build_today_summary(database, TODAY, NOW)

    assert summary["timer"]["title"] == "Write docs"
    assert summary["timer"]["seconds"] == 1800
    assert summary["goals"][0]["completed"] == 1
    assert summary["streak"]["length"] == 1
    assert summary["done_today"] == 1


def test_same_day_tasks_are_ordered_by_id(setup):
    database, manager = setup
    manager.create_task("First", due_date="2026-11-10")
    manager.create_task("Second", due_date="2026-11-10")

    assert titles(build_today_summary(database, TODAY, NOW)["due_today"]) == ["First", "Second"]
