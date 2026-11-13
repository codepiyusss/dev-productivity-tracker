import pytest

from src.database import Database
from src.dependencies import DependencyManager
from src.tasks import TaskManager


@pytest.fixture
def setup():
    database = Database(":memory:")
    manager = TaskManager(database)
    for title in ("A", "B", "C"):
        manager.create_task(title)
    dependencies = DependencyManager(database)
    dependencies.add(3, 1)
    dependencies.add(3, 2)
    return dependencies, manager


def titles(tasks):
    return [t.title for t in tasks]


def test_pending_blockers_are_listed(setup):
    dependencies, _ = setup

    assert titles(dependencies.get_blockers(3)) == ["A", "B"]
    assert dependencies.get_blockers(1) == []


def test_completed_blockers_are_hidden_by_default(setup):
    dependencies, manager = setup
    manager.complete_task(1)

    assert titles(dependencies.get_blockers(3)) == ["B"]
    assert titles(dependencies.get_blockers(3, pending_only=False)) == ["A", "B"]


def test_is_blocked_while_any_blocker_is_unfinished(setup):
    dependencies, manager = setup

    assert dependencies.is_blocked(3) is True

    manager.complete_task(1)
    assert dependencies.is_blocked(3) is True

    manager.complete_task(2)
    assert dependencies.is_blocked(3) is False


def test_tasks_without_blockers_are_not_blocked(setup):
    dependencies, _ = setup

    assert dependencies.is_blocked(1) is False


def test_completed_task_is_never_reported_as_blocked(setup):
    dependencies, manager = setup
    manager.complete_task(3)

    assert dependencies.is_blocked(3) is False


def test_unknown_task_is_not_blocked(setup):
    dependencies, _ = setup

    assert dependencies.is_blocked(99) is False
    assert dependencies.get_blockers(99) == []


def test_reopening_a_blocker_blocks_again(setup):
    dependencies, manager = setup
    manager.complete_task(1)
    manager.complete_task(2)
    assert dependencies.is_blocked(3) is False

    manager.reopen_task(2)

    assert dependencies.is_blocked(3) is True
