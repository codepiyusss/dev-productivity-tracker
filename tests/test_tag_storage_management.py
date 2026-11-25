import pytest

from src.database import Database
from src.tasks import TaskManager


@pytest.fixture
def setup():
    database = Database(":memory:")
    manager = TaskManager(database)
    manager.create_task("A", tags=["bug", "urgent"])
    manager.create_task("B", tags=["bug"])
    manager.create_task("C", tags=["fix", "bug"])
    manager.create_task("D", tags=["fix"])
    manager.create_task("E")
    return database, manager


def tags_of(manager, task_id):
    return sorted(manager.get_task(task_id).tags)


def test_merge_moves_tasks_to_the_target_tag(setup):
    database, manager = setup

    moved = database.merge_tags("fix", "bugfix")

    assert moved == 2
    assert tags_of(manager, 3) == ["bug", "bugfix"]
    assert tags_of(manager, 4) == ["bugfix"]
    assert "fix" not in database.get_tag_counts()


def test_merge_into_an_existing_tag_does_not_duplicate(setup):
    database, manager = setup

    moved = database.merge_tags("fix", "bug")

    assert moved == 2
    assert tags_of(manager, 3) == ["bug"]       # had both: now just "bug"
    assert tags_of(manager, 4) == ["bug"]
    assert database.get_tag_counts()["bug"] == 4


def test_merge_of_an_unknown_tag_changes_nothing(setup):
    database, _ = setup
    before = database.get_tag_counts()

    assert database.merge_tags("ghost", "bug") == 0
    assert database.get_tag_counts() == before


def test_other_tasks_and_tags_are_untouched(setup):
    database, manager = setup

    database.merge_tags("fix", "bugfix")

    assert tags_of(manager, 1) == ["bug", "urgent"]
    assert tags_of(manager, 5) == []


def test_delete_tag_removes_it_everywhere(setup):
    database, manager = setup

    removed = database.delete_tag("bug")

    assert removed == 3
    assert tags_of(manager, 1) == ["urgent"]
    assert tags_of(manager, 2) == []
    assert "bug" not in database.get_tag_counts()


def test_delete_unknown_tag_returns_zero(setup):
    database, _ = setup

    assert database.delete_tag("ghost") == 0
