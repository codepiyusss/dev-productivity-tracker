import sqlite3

import pytest

from src.backup import describe_database, format_counts
from src.database import Database
from src.goals import GoalTracker
from src.journal import ProductivityJournal
from src.tasks import TaskManager
from src.timetracking import TimeTracker


def build(path):
    database = Database(path)
    manager = TaskManager(database)
    manager.create_task("A")
    manager.create_task("B")
    TimeTracker(database).log_manual(1, 600)
    GoalTracker(database).set_goal("daily", 3)
    ProductivityJournal(path).add_entry(
        achievements="Did things", entry_date="2026-11-10"
    )
    return path


def test_describe_counts_every_table(tmp_path):
    path = build(str(tmp_path / "x.db"))

    info = describe_database(path)

    assert info["counts"] == {
        "tasks": 2, "time_entries": 1, "goals": 1, "journal_entries": 1,
    }
    assert info["size_bytes"] > 0


def test_missing_tables_count_as_zero(tmp_path):
    path = str(tmp_path / "old.db")
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("CREATE TABLE tasks (task_id INTEGER PRIMARY KEY, title TEXT)")
        connection.execute("INSERT INTO tasks (title) VALUES ('Old')")
    connection.close()

    assert describe_database(path)["counts"] == {
        "tasks": 1, "time_entries": 0, "goals": 0, "journal_entries": 0,
    }


def test_describe_does_not_modify_the_file(tmp_path):
    path = build(str(tmp_path / "x.db"))
    before = open(path, "rb").read()

    describe_database(path)

    assert open(path, "rb").read() == before


def test_describe_rejects_missing_file(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        describe_database(str(tmp_path / "nope.db"))


def test_describe_rejects_files_that_are_not_databases(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("not sqlite at all" * 100)

    with pytest.raises(ValueError, match="Not a readable database"):
        describe_database(str(bad))


def test_describe_rejects_other_sqlite_databases(tmp_path):
    path = str(tmp_path / "other.db")
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("CREATE TABLE notes (text TEXT)")
    connection.close()

    with pytest.raises(ValueError, match="does not look like a tracker database"):
        describe_database(path)


def test_format_counts():
    assert format_counts(
        {"tasks": 12, "time_entries": 3, "goals": 0, "journal_entries": 5}
    ) == "12 tasks, 3 time entries, 5 journal entries"
    assert format_counts(
        {"tasks": 0, "time_entries": 0, "goals": 0, "journal_entries": 0}
    ) == "empty"
