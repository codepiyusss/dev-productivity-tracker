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
    dependencies.add(2, 1)
    dependencies.add(3, 2)
    return dependencies, database


def test_remove_deletes_only_that_link(setup):
    dependencies, database = setup

    dependencies.remove(2, 1)

    assert database.get_all_dependencies() == [(3, 2)]


def test_removing_a_missing_link_is_an_error(setup):
    dependencies, database = setup

    with pytest.raises(ValueError, match="Task 1 does not depend on task 2"):
        dependencies.remove(1, 2)       # the reverse of a real link

    assert len(database.get_all_dependencies()) == 2


def test_removing_twice_fails_the_second_time(setup):
    dependencies, _ = setup
    dependencies.remove(2, 1)

    with pytest.raises(ValueError, match="does not depend"):
        dependencies.remove(2, 1)


def test_a_removed_link_can_be_added_again(setup):
    dependencies, database = setup
    dependencies.remove(2, 1)

    dependencies.add(2, 1)

    assert (2, 1) in database.get_all_dependencies()


def test_removing_a_link_allows_one_that_was_a_loop(setup):
    dependencies, database = setup
    dependencies.remove(3, 2)      # 3 no longer waits on 2

    dependencies.add(1, 3)         # would have been a loop before

    assert (1, 3) in database.get_all_dependencies()
