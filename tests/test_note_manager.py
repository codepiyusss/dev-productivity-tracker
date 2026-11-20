from datetime import datetime

import pytest

from src.database import Database
from src.notes import MAX_NOTE_LENGTH, NoteManager
from src.tasks import TaskManager

NOW = datetime(2026, 11, 10, 9, 30, 15)


@pytest.fixture
def notes():
    database = Database(":memory:")
    TaskManager(database).create_task("Write docs")
    return NoteManager(database)


def test_add_saves_a_stamped_note(notes):
    note = notes.add(1, "Check the CLI examples", NOW)

    assert note["text"] == "Check the CLI examples"
    assert note["created_at"] == "2026-11-10T09:30:15"
    assert notes.list(1) == [note]


def test_text_is_trimmed_but_inner_newlines_are_kept(notes):
    note = notes.add(1, "  line one\nline two  \n", NOW)

    assert note["text"] == "line one\nline two"


def test_notes_are_listed_oldest_first(notes):
    notes.add(1, "later", datetime(2026, 11, 11, 9, 0, 0))
    notes.add(1, "earlier", datetime(2026, 11, 10, 9, 0, 0))

    assert [n["text"] for n in notes.list(1)] == ["earlier", "later"]


def test_unknown_task_is_rejected(notes):
    with pytest.raises(ValueError, match="Task 9 not found"):
        notes.add(9, "hello", NOW)


@pytest.mark.parametrize("text", ["", "   ", "\n\t", None])
def test_empty_notes_are_rejected(notes, text):
    with pytest.raises(ValueError, match="cannot be empty"):
        notes.add(1, text, NOW)

    assert notes.list(1) == []


def test_length_limit(notes):
    notes.add(1, "x" * MAX_NOTE_LENGTH, NOW)

    with pytest.raises(ValueError, match="longer than 2000 characters"):
        notes.add(1, "x" * (MAX_NOTE_LENGTH + 1), NOW)

    assert len(notes.list(1)) == 1


def test_delete_returns_the_note_and_removes_it(notes):
    note = notes.add(1, "temporary", NOW)

    deleted = notes.delete(note["note_id"])

    assert deleted["text"] == "temporary"
    assert notes.list(1) == []


def test_deleting_a_missing_note_is_an_error(notes):
    with pytest.raises(ValueError, match="Note 5 not found"):
        notes.delete(5)


def test_defaults_to_the_current_time(notes):
    before = datetime.now().replace(microsecond=0)

    note = notes.add(1, "now")

    assert datetime.strptime(note["created_at"], "%Y-%m-%dT%H:%M:%S") >= before
