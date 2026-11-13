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
    dependencies.add(2, 1)
    dependencies.add(3, 1)
    dependencies.add(4, 2)
    return dependencies, manager


def titles(tasks):
    return [t.title for t in tasks]


def test_dependents_are_the_tasks_waiting_on_this_one(setup):
    dependencies, _ = setup

    assert titles(dependencies.get_dependents(1)) == ["B", "C"]
    assert titles(dependencies.get_dependents(2)) == ["D"]
    assert dependencies.get_dependents(4) == []


def test_completed_dependents_are_hidden_by_default(setup):
    dependencies, manager = setup
    manager.complete_task(2)

    assert titles(dependencies.get_dependents(1)) == ["C"]
    assert titles(dependencies.get_dependents(1, pending_only=False)) == ["B", "C"]


def test_only_direct_dependents_are_returned(setup):
    dependencies, _ = setup

    assert "D" not in titles(dependencies.get_dependents(1))


def test_dependents_of_unknown_task_is_empty(setup):
    dependencies, _ = setup

    assert dependencies.get_dependents(99) == []


def test_dependents_and_blockers_mirror_each_other(setup):
    dependencies, _ = setup

    for task_id in (1, 2, 3, 4):
        for dependent in dependencies.get_dependents(task_id, pending_only=False):
            blocker_ids = [t.task_id for t in
                           dependencies.get_blockers(dependent.task_id, pending_only=False)]
            assert task_id in blocker_ids
