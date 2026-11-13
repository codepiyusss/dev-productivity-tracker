import sqlite3

import pytest

from src.database import Database
from src.models.task import Task


@pytest.fixture
def database():
    db = Database(":memory:")
    for title in ("A", "B", "C"):
        db.add_task(Task(title))
    return db


def test_no_dependencies_by_default(database):
    assert database.get_all_dependencies() == []
    assert database.get_blocker_ids(1) == []
    assert database.get_dependent_ids(1) == []


def test_add_and_read_dependencies_in_both_directions(database):
    database.add_dependency(3, 1)   # C waits on A
    database.add_dependency(3, 2)   # C waits on B
    database.add_dependency(2, 1)   # B waits on A

    assert database.get_blocker_ids(3) == [1, 2]
    assert database.get_dependent_ids(1) == [2, 3]
    assert database.get_all_dependencies() == [(2, 1), (3, 1), (3, 2)]


def test_duplicate_dependency_is_rejected(database):
    database.add_dependency(2, 1)

    with pytest.raises(sqlite3.IntegrityError):
        database.add_dependency(2, 1)


def test_task_cannot_depend_on_itself(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.add_dependency(1, 1)


def test_dependency_on_a_missing_task_is_rejected(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.add_dependency(1, 99)
    with pytest.raises(sqlite3.IntegrityError):
        database.add_dependency(99, 1)


def test_remove_dependency(database):
    database.add_dependency(2, 1)

    assert database.remove_dependency(2, 1) is True
    assert database.remove_dependency(2, 1) is False
    assert database.get_blocker_ids(2) == []


def test_removing_one_direction_leaves_the_other(database):
    database.add_dependency(2, 1)
    database.add_dependency(1, 3)

    database.remove_dependency(2, 1)

    assert database.get_all_dependencies() == [(1, 3)]


def test_deleting_either_task_removes_its_dependencies(database):
    database.add_dependency(2, 1)
    database.add_dependency(3, 2)
    database.add_dependency(3, 1)

    database.delete_task(2)

    assert database.get_all_dependencies() == [(3, 1)]


def test_existing_database_gains_the_table(tmp_path):
    path = str(tmp_path / "old.db")
    first = Database(path)
    first.add_task(Task("A"))
    first.add_task(Task("B"))
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("DROP TABLE task_dependencies")
    connection.close()

    reopened = Database(path)
    reopened.add_dependency(2, 1)

    assert reopened.get_all_dependencies() == [(2, 1)]
