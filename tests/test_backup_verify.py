import sqlite3

from src.backup import copy_database, verify_database
from src.database import Database
from src.tasks import TaskManager


def healthy(tmp_path):
    path = str(tmp_path / "ok.db")
    manager = TaskManager(Database(path))
    manager.create_task("A", tags=["x"])
    return path


def test_healthy_database_has_no_problems(tmp_path):
    assert verify_database(healthy(tmp_path)) == []


def test_empty_but_valid_database_is_healthy(tmp_path):
    path = str(tmp_path / "empty.db")
    Database(path)

    assert verify_database(path) == []


def test_missing_file_is_reported(tmp_path):
    problems = verify_database(str(tmp_path / "nope.db"))

    assert len(problems) == 1 and "not found" in problems[0]


def test_garbage_file_is_reported(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("garbage" * 500)

    problems = verify_database(str(bad))

    assert len(problems) == 1 and "Not a readable database" in problems[0]


def test_unrelated_sqlite_file_is_reported(tmp_path):
    path = str(tmp_path / "other.db")
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("CREATE TABLE notes (text TEXT)")
    connection.close()

    assert "does not look like a tracker database" in verify_database(path)[0]


def test_orphaned_rows_are_reported(tmp_path):
    path = healthy(tmp_path)
    connection = sqlite3.connect(path)  # foreign keys are off by default here
    with connection:
        connection.execute("INSERT INTO task_tags (task_id, tag) VALUES (999, 'ghost')")
    connection.close()

    problems = verify_database(path)

    assert len(problems) == 1 and "point to records that no longer exist" in problems[0]


def test_corrupted_pages_are_reported(tmp_path):
    path = healthy(tmp_path)
    data = bytearray(open(path, "rb").read())
    page_size = int.from_bytes(data[16:18], "big") or 65536
    # Overwrite the b-tree header of page 2 (the first table's root page)
    # but keep the file header on page 1 readable.
    for index in range(page_size, page_size + 64):
        data[index] = 0xFF
    open(path, "wb").write(bytes(data))

    problems = verify_database(path)

    assert problems  # some kind of integrity or database error


def test_a_fresh_snapshot_verifies(tmp_path):
    snapshot = copy_database(healthy(tmp_path), str(tmp_path / "snap.db"))

    assert verify_database(snapshot) == []


def test_verification_does_not_modify_the_file(tmp_path):
    path = healthy(tmp_path)
    before = open(path, "rb").read()

    verify_database(path)

    assert open(path, "rb").read() == before
