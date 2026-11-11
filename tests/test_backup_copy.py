import sqlite3

import pytest

from src.backup import copy_database
from src.database import Database
from src.models.task import Task
from src.tasks import TaskManager


@pytest.fixture
def source(tmp_path):
    path = str(tmp_path / "source.db")
    manager = TaskManager(Database(path))
    manager.create_task("Write docs", tags=["work"])
    manager.create_task("Fix bug")
    return path


def titles(path):
    return sorted(t.title for t in Database(path).get_all_tasks())


def test_copy_contains_all_the_data(source, tmp_path):
    result = copy_database(source, str(tmp_path / "copy.db"))

    assert result == str(tmp_path / "copy.db")
    assert titles(result) == ["Fix bug", "Write docs"]
    assert Database(result).get_all_tasks()[0].tags in (["work"], [])


def test_copy_is_a_snapshot_not_a_link(source, tmp_path):
    copy = copy_database(source, str(tmp_path / "copy.db"))

    TaskManager(Database(source)).create_task("Added later")

    assert titles(copy) == ["Fix bug", "Write docs"]


def test_copy_creates_missing_folders(source, tmp_path):
    result = copy_database(source, str(tmp_path / "a" / "b" / "copy.db"))

    assert titles(result) == ["Fix bug", "Write docs"]


def test_copy_never_overwrites_an_existing_file(source, tmp_path):
    existing = tmp_path / "copy.db"
    existing.write_text("precious")

    with pytest.raises(ValueError, match="already exists"):
        copy_database(source, str(existing))

    assert existing.read_text() == "precious"


def test_missing_source_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        copy_database(str(tmp_path / "nope.db"), str(tmp_path / "copy.db"))

    assert not (tmp_path / "copy.db").exists()


def test_source_that_is_not_a_database_is_rejected_cleanly(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("this is not a database" * 100)

    with pytest.raises(ValueError, match="Could not copy"):
        copy_database(str(bad), str(tmp_path / "copy.db"))

    assert not (tmp_path / "copy.db").exists()
    assert not (tmp_path / "copy.db.tmp").exists()


def test_copy_works_while_the_source_has_an_open_connection(source, tmp_path):
    connection = sqlite3.connect(source)
    connection.execute("SELECT * FROM tasks").fetchall()

    result = copy_database(source, str(tmp_path / "copy.db"))
    connection.close()

    assert titles(result) == ["Fix bug", "Write docs"]


def test_source_is_left_unchanged(source, tmp_path):
    before = open(source, "rb").read()

    copy_database(source, str(tmp_path / "copy.db"))

    assert open(source, "rb").read() == before
