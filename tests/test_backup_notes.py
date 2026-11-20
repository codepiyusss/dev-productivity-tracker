from src.backup import create_backup, format_counts, restore_backup
from src.database import Database
from src.notes import NoteManager
from src.tasks import TaskManager


def build(path):
    database = Database(path)
    TaskManager(database).create_task("A")
    notes = NoteManager(database)
    notes.add(1, "first")
    notes.add(1, "second")
    return database


def test_notes_are_counted_in_a_backup(tmp_path):
    db = str(tmp_path / "t.db")
    build(db)

    info = create_backup(db, tmp_path / "b")

    assert info["counts"]["task_notes"] == 2
    assert format_counts(info["counts"]) == "1 task, 2 notes"


def test_a_single_note_is_singular():
    counts = {"tasks": 1, "task_notes": 1}

    assert format_counts(counts) == "1 task, 1 note"


def test_restore_brings_notes_back(tmp_path):
    db = str(tmp_path / "t.db")
    database = build(db)
    backup = create_backup(db, tmp_path / "b")["path"]
    database.delete_note(1)
    database.delete_note(2)
    assert Database(db).get_notes(1) == []

    restore_backup(backup, db)

    assert [n["text"] for n in Database(db).get_notes(1)] == ["first", "second"]
