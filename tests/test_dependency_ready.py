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
    dependencies.add(3, 1)      # C waits on A and B
    dependencies.add(3, 2)
    return dependencies, manager


def titles(tasks):
    return sorted(t.title for t in tasks)


def test_blocker_map_lists_unfinished_blockers(setup):
    dependencies, _ = setup

    assert dependencies.get_blocker_map() == {2: [1], 3: [1, 2]}


def test_blocked_and_ready_split_the_pending_tasks(setup):
    dependencies, _ = setup

    assert titles(dependencies.get_blocked_tasks()) == ["B", "C"]
    assert titles(dependencies.get_ready_tasks()) == ["A", "D"]


def test_finishing_a_blocker_unblocks_what_it_alone_held_up(setup):
    dependencies, manager = setup
    manager.complete_task(1)

    assert titles(dependencies.get_ready_tasks()) == ["B", "D"]
    assert titles(dependencies.get_blocked_tasks()) == ["C"]   # still needs B


def test_everything_becomes_ready_when_all_blockers_are_done(setup):
    dependencies, manager = setup
    manager.complete_task(1)
    manager.complete_task(2)

    assert titles(dependencies.get_ready_tasks()) == ["C", "D"]
    assert dependencies.get_blocked_tasks() == []
    assert dependencies.get_blocker_map() == {}


def test_completed_tasks_are_in_neither_list(setup):
    dependencies, manager = setup
    manager.complete_task(4)
    manager.complete_task(2)

    assert "D" not in titles(dependencies.get_ready_tasks())
    assert "B" not in titles(dependencies.get_blocked_tasks())


def test_no_dependencies_means_everything_pending_is_ready():
    database = Database(":memory:")
    manager = TaskManager(database)
    manager.create_task("A")
    manager.create_task("B")

    dependencies = DependencyManager(database)

    assert titles(dependencies.get_ready_tasks()) == ["A", "B"]
    assert dependencies.get_blocked_tasks() == []


def test_deleting_a_blocker_unblocks_its_dependents(setup):
    dependencies, manager = setup
    manager.delete_task(1)

    assert titles(dependencies.get_blocked_tasks()) == ["C"]   # still waits on B
    assert "B" in titles(dependencies.get_ready_tasks())
