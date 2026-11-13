import pytest

from src.database import Database
from src.dependencies import DependencyManager
from src.tasks import TaskManager


@pytest.fixture
def setup():
    database = Database(":memory:")
    manager = TaskManager(database)
    for title in ("A", "B", "C", "D"):
        manager.create_task(title)
    dependencies = DependencyManager(database)
    dependencies.add(2, 1)      # B waits on A
    dependencies.add(3, 1)      # C waits on A and D
    dependencies.add(3, 4)
    return dependencies, manager


def titles(tasks):
    return sorted(t.title for t in tasks)


def test_completing_the_only_blocker_frees_the_task(setup):
    dependencies, manager = setup
    manager.complete_task(1)

    assert titles(dependencies.get_newly_ready(1)) == ["B"]


def test_a_task_with_another_open_blocker_is_not_freed(setup):
    dependencies, manager = setup
    manager.complete_task(1)

    assert "C" not in titles(dependencies.get_newly_ready(1))


def test_completing_the_last_blocker_frees_it_later(setup):
    dependencies, manager = setup
    manager.complete_task(1)
    manager.complete_task(4)

    assert titles(dependencies.get_newly_ready(4)) == ["C"]


def test_task_nobody_waits_on_frees_nothing(setup):
    dependencies, manager = setup
    manager.complete_task(2)

    assert dependencies.get_newly_ready(2) == []


def test_already_completed_dependents_are_not_reported(setup):
    dependencies, manager = setup
    manager.complete_task(2)
    manager.complete_task(1)

    assert titles(dependencies.get_newly_ready(1)) == []


def test_before_completion_nothing_is_freed(setup):
    dependencies, _ = setup

    assert dependencies.get_newly_ready(1) == []
