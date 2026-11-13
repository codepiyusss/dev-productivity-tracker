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
    return DependencyManager(database), database


def test_add_links_the_tasks(setup):
    dependencies, database = setup

    dependencies.add(2, 1)

    assert database.get_blocker_ids(2) == [1]


def test_unknown_tasks_are_rejected(setup):
    dependencies, database = setup

    with pytest.raises(ValueError, match="Task 9 not found"):
        dependencies.add(9, 1)
    with pytest.raises(ValueError, match="Task 9 not found"):
        dependencies.add(1, 9)

    assert database.get_all_dependencies() == []


def test_self_dependency_is_rejected(setup):
    dependencies, _ = setup

    with pytest.raises(ValueError, match="cannot depend on itself"):
        dependencies.add(1, 1)


def test_repeated_link_is_rejected(setup):
    dependencies, database = setup
    dependencies.add(2, 1)

    with pytest.raises(ValueError, match="already depends on task 1"):
        dependencies.add(2, 1)

    assert database.get_all_dependencies() == [(2, 1)]


def test_direct_loop_is_rejected(setup):
    dependencies, database = setup
    dependencies.add(2, 1)

    with pytest.raises(ValueError, match="circular dependency: 1 -> 2 -> 1"):
        dependencies.add(1, 2)

    assert database.get_all_dependencies() == [(2, 1)]


def test_indirect_loop_is_rejected_with_the_chain(setup):
    dependencies, database = setup
    dependencies.add(3, 2)
    dependencies.add(2, 1)

    with pytest.raises(ValueError, match="circular dependency: 1 -> 3 -> 2 -> 1"):
        dependencies.add(1, 3)

    assert len(database.get_all_dependencies()) == 2


def test_chains_and_diamonds_are_allowed(setup):
    dependencies, database = setup

    dependencies.add(2, 1)
    dependencies.add(3, 2)
    dependencies.add(3, 1)   # shortcut, not a loop

    assert database.get_all_dependencies() == [(2, 1), (3, 1), (3, 2)]


def test_completed_tasks_can_still_be_linked(setup):
    dependencies, database = setup
    TaskManager(database).complete_task(1)

    dependencies.add(2, 1)

    assert database.get_blocker_ids(2) == [1]
