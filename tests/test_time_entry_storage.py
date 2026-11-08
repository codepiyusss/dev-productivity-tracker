import sqlite3

import pytest

from src.database import Database
from src.models.task import Task


@pytest.fixture
def database():
    db = Database(":memory:")
    db.add_task(Task("First"))
    db.add_task(Task("Second"))
    return db


def test_add_and_list_entries(database):
    entry = database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")

    assert entry["entry_id"] == 1
    assert database.get_time_entries() == [entry]


def test_running_entry_has_no_end(database):
    database.add_time_entry(1, "2026-11-10T09:00:00")

    running = database.get_running_entry()

    assert running["task_id"] == 1
    assert running["ended_at"] is None


def test_no_running_entry_when_all_finished(database):
    database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")

    assert database.get_running_entry() is None


def test_only_one_entry_can_run_at_a_time(database):
    database.add_time_entry(1, "2026-11-10T09:00:00")

    with pytest.raises(sqlite3.IntegrityError):
        database.add_time_entry(2, "2026-11-10T09:30:00")


def test_finished_entries_do_not_block_a_new_timer(database):
    database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")
    database.add_time_entry(1, "2026-11-10T11:00:00", "2026-11-10T12:00:00")

    database.add_time_entry(2, "2026-11-10T13:00:00")

    assert database.get_running_entry()["task_id"] == 2


def test_end_time_entry(database):
    entry = database.add_time_entry(1, "2026-11-10T09:00:00")

    assert database.end_time_entry(entry["entry_id"], "2026-11-10T09:45:00") is True
    assert database.get_running_entry() is None
    assert database.get_time_entries()[0]["ended_at"] == "2026-11-10T09:45:00"


def test_ending_twice_or_unknown_entry_returns_false(database):
    entry = database.add_time_entry(1, "2026-11-10T09:00:00")
    database.end_time_entry(entry["entry_id"], "2026-11-10T09:45:00")

    assert database.end_time_entry(entry["entry_id"], "2026-11-10T10:00:00") is False
    assert database.end_time_entry(999, "2026-11-10T10:00:00") is False
    assert database.get_time_entries()[0]["ended_at"] == "2026-11-10T09:45:00"


def test_end_before_start_is_rejected(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T08:00:00")


def test_filter_by_task_and_date_range(database):
    database.add_time_entry(1, "2026-11-09T09:00:00", "2026-11-09T10:00:00")
    database.add_time_entry(2, "2026-11-10T09:00:00", "2026-11-10T10:00:00")
    database.add_time_entry(1, "2026-11-11T09:00:00", "2026-11-11T10:00:00")

    assert len(database.get_time_entries(task_id=1)) == 2
    assert len(database.get_time_entries(since="2026-11-10T00:00:00")) == 2
    assert len(database.get_time_entries(until="2026-11-11T00:00:00")) == 2
    assert [e["task_id"] for e in database.get_time_entries(
        since="2026-11-10T00:00:00", until="2026-11-11T00:00:00")] == [2]


def test_entries_are_ordered_by_start_time(database):
    database.add_time_entry(1, "2026-11-11T09:00:00", "2026-11-11T10:00:00")
    database.add_time_entry(1, "2026-11-09T09:00:00", "2026-11-09T10:00:00")

    starts = [e["started_at"] for e in database.get_time_entries()]

    assert starts == sorted(starts)


def test_delete_time_entry(database):
    entry = database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")

    assert database.delete_time_entry(entry["entry_id"]) is True
    assert database.delete_time_entry(entry["entry_id"]) is False
    assert database.get_time_entries() == []


def test_deleting_a_task_removes_its_time_entries(database):
    database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")
    database.add_time_entry(2, "2026-11-10T11:00:00", "2026-11-10T12:00:00")

    database.delete_task(1)

    assert [e["task_id"] for e in database.get_time_entries()] == [2]


def test_entry_for_missing_task_is_rejected(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.add_time_entry(99, "2026-11-10T09:00:00")


def test_existing_database_gains_time_tracking_table(tmp_path):
    path = str(tmp_path / "old.db")
    first = Database(path)
    first.add_task(Task("Old task"))
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("DROP TABLE time_entries")
    connection.close()

    reopened = Database(path)
    reopened.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")

    assert len(reopened.get_time_entries()) == 1
