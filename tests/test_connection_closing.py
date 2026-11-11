import gc
import os
import sqlite3

import pytest

from src.database import Database
from src.journal import ProductivityJournal
from src.models.task import Task
from src.sqlite_utils import ClosingConnection
from src.tasks import TaskManager


def test_with_block_closes_the_connection(tmp_path):
    connection = sqlite3.connect(str(tmp_path / "x.db"), factory=ClosingConnection)

    with connection:
        connection.execute("CREATE TABLE t (a INTEGER)")

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_with_block_still_commits(tmp_path):
    path = str(tmp_path / "x.db")
    with sqlite3.connect(path, factory=ClosingConnection) as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
        connection.execute("INSERT INTO t VALUES (1)")

    with sqlite3.connect(path, factory=ClosingConnection) as connection:
        assert connection.execute("SELECT a FROM t").fetchall() == [(1,)]


def test_error_rolls_back_and_still_closes(tmp_path):
    path = str(tmp_path / "x.db")
    with sqlite3.connect(path, factory=ClosingConnection) as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")

    failing = sqlite3.connect(path, factory=ClosingConnection)
    with pytest.raises(RuntimeError):
        with failing:
            failing.execute("INSERT INTO t VALUES (1)")
            raise RuntimeError("boom")

    with pytest.raises(sqlite3.ProgrammingError):
        failing.execute("SELECT 1")
    with sqlite3.connect(path, factory=ClosingConnection) as connection:
        assert connection.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0


def test_database_connections_are_closed_after_each_use():
    database = Database(":memory:")

    with database._connect() as connection:
        connection.execute("SELECT 1")

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_journal_connections_are_closed_after_each_use():
    journal = ProductivityJournal(":memory:")

    with journal._connect() as connection:
        connection.execute("SELECT 1")

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_database_file_can_be_replaced_right_after_use(tmp_path):
    """On Windows this fails if any connection is still open."""
    path = tmp_path / "live.db"
    manager = TaskManager(Database(str(path)))
    manager.create_task("A", tags=["x"])
    manager.get_all_tasks()
    manager.complete_task(1)
    manager.delete_task(1)
    ProductivityJournal(str(path)).add_entry(achievements="done")

    replacement = tmp_path / "other.db"
    replacement.write_bytes(b"replacement")
    os.replace(replacement, path)

    assert path.read_bytes() == b"replacement"
    os.remove(path)


@pytest.mark.skipif(
    not os.path.isdir("/proc/self/fd"), reason="needs /proc to list open files"
)
def test_no_file_handles_are_left_open_without_garbage_collection(tmp_path):
    path = tmp_path / "live.db"

    def open_handles():
        found = 0
        for fd in os.listdir("/proc/self/fd"):
            try:
                if os.readlink(f"/proc/self/fd/{fd}") == str(path):
                    found += 1
            except OSError:
                pass
        return found

    gc.collect()
    gc.disable()
    try:
        manager = TaskManager(Database(str(path)))
        for number in range(5):
            manager.create_task(f"Task {number}", tags=["x"])
        manager.get_all_tasks()
        manager.database.set_goal("daily", 3)
        manager.database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")
        ProductivityJournal(str(path)).add_entry(achievements="done")

        assert open_handles() == 0
    finally:
        gc.enable()
