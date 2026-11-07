import pytest

from src.database import Database
from src.tasks import TaskManager
from src.utils import validate_due_date


@pytest.fixture
def manager():
    return TaskManager(Database(":memory:"))


@pytest.mark.parametrize("value, expected", [
    ("2026-12-01", "2026-12-01"),
    (" 2026-12-01 ", "2026-12-01"),
    ("2026-1-5", "2026-01-05"),
    (None, None),
    ("", None),
    ("   ", None),
])
def test_validate_due_date_accepts_and_normalizes(value, expected):
    assert validate_due_date(value) == expected


@pytest.mark.parametrize("value", [
    "31-12-2026", "2026/12/01", "2026-13-01", "2026-02-30", "tomorrow", "2026",
])
def test_validate_due_date_rejects_bad_values(value):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        validate_due_date(value)


def test_create_task_rejects_invalid_due_date(manager):
    with pytest.raises(ValueError):
        manager.create_task("Ship it", due_date="31-12-2026")

    assert manager.get_all_tasks() == []


def test_create_task_normalizes_due_date(manager):
    task = manager.create_task("Ship it", due_date="2026-1-5")

    assert manager.get_task(task.task_id).due_date == "2026-01-05"


def test_update_task_rejects_invalid_due_date(manager):
    task = manager.create_task("Ship it", due_date="2026-12-01")

    with pytest.raises(ValueError):
        manager.update_task(task.task_id, due_date="soon")

    assert manager.get_task(task.task_id).due_date == "2026-12-01"


def test_update_task_can_clear_due_date(manager):
    task = manager.create_task("Ship it", due_date="2026-12-01")

    manager.update_task(task.task_id, due_date=None)

    assert manager.get_task(task.task_id).due_date is None


def test_update_task_rejects_invalid_priority_and_empty_title(manager):
    task = manager.create_task("Ship it", priority="low")

    with pytest.raises(ValueError, match="Priority"):
        manager.update_task(task.task_id, priority="urgent")

    with pytest.raises(ValueError, match="title"):
        manager.update_task(task.task_id, title="   ")

    saved = manager.get_task(task.task_id)
    assert (saved.title, saved.priority) == ("Ship it", "low")


def test_update_task_still_works_for_valid_changes(manager):
    task = manager.create_task("Ship it")

    updated = manager.update_task(
        task.task_id, title="Ship v2", priority="high", due_date="2026-12-24"
    )

    assert (updated.title, updated.priority, updated.due_date) == (
        "Ship v2", "high", "2026-12-24"
    )


def test_loading_old_rows_with_bad_dates_does_not_crash(manager):
    # Databases created before validation may hold odd values; listing
    # must keep working rather than failing on them.
    from src.models.task import Task
    manager.database.add_task(Task("Legacy", due_date="31-12-2026"))

    assert manager.get_all_tasks()[0].due_date == "31-12-2026"
