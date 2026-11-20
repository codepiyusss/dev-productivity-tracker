import sqlite3

import pytest

from src.database import Database
from src.models.task import Task


@pytest.fixture
def database():
    db = Database(":memory:")
    db.add_task(Task("A"))
    db.add_task(Task("B"))
    return db


def test_no_notes_by_default(database):
    assert database.get_notes(1) == []
    assert database.get_note_counts() == {}


def test_add_and_read_notes_oldest_first(database):
    database.add_note(1, "second", "2026-11-10T10:00:00")
    first = database.add_note(1, "first", "2026-11-10T09:00:00")

    assert first == {"note_id": 2, "task_id": 1, "text": "first", "created_at": "2026-11-10T09:00:00"}
    assert [n["text"] for n in database.get_notes(1)] == ["first", "second"]


def test_notes_are_kept_per_task(database):
    database.add_note(1, "for A", "2026-11-10T09:00:00")
    database.add_note(2, "for B", "2026-11-10T09:00:00")

    assert [n["text"] for n in database.get_notes(1)] == ["for A"]
    assert database.get_note_counts() == {1: 1, 2: 1}


def test_get_and_delete_a_note(database):
    note = database.add_note(1, "hello", "2026-11-10T09:00:00")

    assert database.get_note(note["note_id"])["text"] == "hello"
    assert database.delete_note(note["note_id"]) is True
    assert database.delete_note(note["note_id"]) is False
    assert database.get_note(note["note_id"]) is None


def test_blank_notes_are_rejected_by_the_database(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.add_note(1, "   ", "2026-11-10T09:00:00")


def test_note_for_a_missing_task_is_rejected(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.add_note(99, "orphan", "2026-11-10T09:00:00")


def test_deleting_a_task_deletes_its_notes(database):
    database.add_note(1, "gone soon", "2026-11-10T09:00:00")
    database.add_note(2, "stays", "2026-11-10T09:00:00")

    database.delete_task(1)

    assert database.get_note_counts() == {2: 1}


def test_existing_database_gains_the_table(tmp_path):
    path = str(tmp_path / "old.db")
    first = Database(path)
    first.add_task(Task("A"))
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("DROP TABLE task_notes")
    connection.close()

    reopened = Database(path)
    reopened.add_note(1, "works again", "2026-11-10T09:00:00")

    assert reopened.get_notes(1)[0]["text"] == "works again"
