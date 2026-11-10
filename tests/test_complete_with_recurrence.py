from datetime import date

import pytest

from src.database import Database
from src.tasks import TaskManager

TODAY = date(2026, 11, 10)


@pytest.fixture
def manager():
    return TaskManager(Database(":memory:"))


def pending_titles(manager):
    return [t.title for t in manager.get_all_tasks() if not t.completed]


def test_completing_a_repeating_task_creates_the_next_one(manager):
    task = manager.create_task(
        "Standup", description="Daily sync", priority="high", category="work",
        due_date="2026-11-10", tags=["team", "daily"], recurrence="daily",
    )

    completed, following = manager.complete_with_recurrence(task.task_id, TODAY)

    assert completed is True
    assert following.task_id != task.task_id
    assert following.due_date == "2026-11-11"
    assert (following.title, following.description) == ("Standup", "Daily sync")
    assert (following.priority, following.category) == ("high", "work")
    assert following.tags == ["team", "daily"]
    assert following.recurrence == "daily"
    assert following.completed is False
    assert manager.get_task(task.task_id).completed is True


def test_the_next_task_keeps_repeating(manager):
    task = manager.create_task("Report", due_date="2026-11-10", recurrence="weekly")

    _, first = manager.complete_with_recurrence(task.task_id, TODAY)
    _, second = manager.complete_with_recurrence(first.task_id, date(2026, 11, 17))

    assert (first.due_date, second.due_date) == ("2026-11-17", "2026-11-24")


def test_late_completion_skips_past_dates(manager):
    task = manager.create_task("Report", due_date="2026-10-01", recurrence="weekly")

    _, following = manager.complete_with_recurrence(task.task_id, TODAY)

    assert following.due_date == "2026-11-12"


def test_plain_tasks_do_not_create_anything(manager):
    task = manager.create_task("One-off", due_date="2026-11-10")

    completed, following = manager.complete_with_recurrence(task.task_id, TODAY)

    assert (completed, following) == (True, None)
    assert len(manager.get_all_tasks()) == 1


def test_missing_task(manager):
    assert manager.complete_with_recurrence(99, TODAY) == (False, None)


def test_completing_an_already_completed_task_does_not_repeat_again(manager):
    task = manager.create_task("Standup", due_date="2026-11-10", recurrence="daily")
    manager.complete_with_recurrence(task.task_id, TODAY)

    completed, following = manager.complete_with_recurrence(task.task_id, TODAY)

    assert (completed, following) == (True, None)
    assert pending_titles(manager) == ["Standup"]


def test_reopen_and_complete_does_not_create_a_duplicate(manager):
    task = manager.create_task("Standup", due_date="2026-11-10", recurrence="daily")
    manager.complete_with_recurrence(task.task_id, TODAY)
    manager.reopen_task(task.task_id)

    _, following = manager.complete_with_recurrence(task.task_id, TODAY)

    assert following is None
    assert pending_titles(manager) == ["Standup"]


def test_plain_complete_task_never_repeats(manager):
    task = manager.create_task("Standup", due_date="2026-11-10", recurrence="daily")

    manager.complete_task(task.task_id)

    assert len(manager.get_all_tasks()) == 1


def test_unreadable_legacy_due_date_does_not_crash(manager):
    from src.models.task import Task
    legacy = manager.database.add_task(
        Task("Legacy", due_date="31-12-2026", recurrence="daily")
    )

    assert manager.complete_with_recurrence(legacy.task_id, TODAY) == (True, None)
