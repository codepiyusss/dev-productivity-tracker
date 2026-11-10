import pytest

from src.database import Database
from src.tasks import TaskManager


@pytest.fixture
def manager():
    return TaskManager(Database(":memory:"))


def test_create_repeating_task(manager):
    task = manager.create_task("Standup", due_date="2026-11-10", recurrence="Daily")

    assert manager.get_task(task.task_id).recurrence == "daily"


def test_repeating_task_requires_a_due_date(manager):
    with pytest.raises(ValueError, match="needs a due date"):
        manager.create_task("Standup", recurrence="daily")

    assert manager.get_all_tasks() == []


def test_unknown_repeat_rule_is_rejected(manager):
    with pytest.raises(ValueError, match="daily, weekly, monthly"):
        manager.create_task("Standup", due_date="2026-11-10", recurrence="yearly")


def test_plain_tasks_are_unaffected(manager):
    task = manager.create_task("Plain")

    assert manager.get_task(task.task_id).recurrence is None


def test_update_can_add_and_remove_repeat(manager):
    task = manager.create_task("Standup", due_date="2026-11-10")

    manager.update_task(task.task_id, recurrence="weekly")
    assert manager.get_task(task.task_id).recurrence == "weekly"

    manager.update_task(task.task_id, recurrence=None)
    assert manager.get_task(task.task_id).recurrence is None


def test_update_cannot_add_repeat_without_a_due_date(manager):
    task = manager.create_task("Standup")

    with pytest.raises(ValueError, match="needs a due date"):
        manager.update_task(task.task_id, recurrence="daily")

    assert manager.get_task(task.task_id).recurrence is None


def test_update_can_add_repeat_and_due_date_together(manager):
    task = manager.create_task("Standup")

    manager.update_task(task.task_id, recurrence="daily", due_date="2026-11-10")

    saved = manager.get_task(task.task_id)
    assert (saved.recurrence, saved.due_date) == ("daily", "2026-11-10")


def test_clearing_the_due_date_of_a_repeating_task_is_rejected(manager):
    task = manager.create_task("Standup", due_date="2026-11-10", recurrence="daily")

    with pytest.raises(ValueError, match="needs a due date"):
        manager.update_task(task.task_id, due_date=None)

    assert manager.get_task(task.task_id).due_date == "2026-11-10"


def test_clearing_due_date_and_repeat_together_is_allowed(manager):
    task = manager.create_task("Standup", due_date="2026-11-10", recurrence="daily")

    manager.update_task(task.task_id, due_date=None, recurrence=None)

    saved = manager.get_task(task.task_id)
    assert (saved.due_date, saved.recurrence) == (None, None)


def test_changing_other_fields_keeps_the_repeat(manager):
    task = manager.create_task("Standup", due_date="2026-11-10", recurrence="weekly")

    manager.update_task(task.task_id, title="Team standup", priority="high")

    assert manager.get_task(task.task_id).recurrence == "weekly"
