import pytest

from src.database import Database
from src.main import format_note, main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    _run("add", "Write docs")
    _run.db = str(tmp_path / "t.db")
    return _run


def test_format_note_single_and_multi_line():
    single = {"note_id": 3, "created_at": "2026-11-10T09:30:15", "text": "hello"}
    multi = {"note_id": 12, "created_at": "2026-11-10T09:30:15", "text": "one\ntwo"}

    assert format_note(single) == "  #3 2026-11-10 09:30  hello"
    assert format_note(multi).splitlines() == [
        "  #12 2026-11-10 09:30  one",
        " " * 24 + "two",
    ]


def test_add_note_without_quotes(run, capsys):
    capsys.readouterr()

    assert run("note", "add", "1", "Check", "the", "examples") == 0

    assert "Note #1 added to task 1: Write docs" in capsys.readouterr().out
    assert Database(run.db).get_notes(1)[0]["text"] == "Check the examples"


def test_list_shows_notes_in_order(run, capsys):
    run("note", "add", "1", "first note")
    run("note", "add", "1", "second note")
    capsys.readouterr()

    assert run("note", "list", "1") == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "Notes for task 1: Write docs"
    assert "first note" in lines[1] and "second note" in lines[2]


def test_list_with_no_notes_and_unknown_task(run, capsys):
    capsys.readouterr()

    assert run("note", "list", "1") == 0
    assert "Task 1 (Write docs) has no notes." in capsys.readouterr().out

    assert run("note", "list", "9") == 1
    assert "Task not found." in capsys.readouterr().out


def test_add_rejects_unknown_tasks_and_blank_notes(run, capsys):
    capsys.readouterr()

    assert run("note", "add", "9", "hello") == 1
    assert "Task 9 not found." in capsys.readouterr().out

    assert run("note", "add", "1", "   ") == 1
    assert "cannot be empty" in capsys.readouterr().out


def test_delete_with_yes(run, capsys):
    run("note", "add", "1", "temporary")
    capsys.readouterr()

    assert run("note", "delete", "1", "--yes") == 0

    assert "Note #1 deleted." in capsys.readouterr().out
    assert Database(run.db).get_notes(1) == []


def test_delete_asks_first_and_cancels_by_default(run, capsys, monkeypatch):
    run("note", "add", "1", "keep me")
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    capsys.readouterr()

    assert run("note", "delete", "1") == 0

    assert "Cancelled. Nothing was deleted." in capsys.readouterr().out
    assert len(Database(run.db).get_notes(1)) == 1


def test_delete_proceeds_when_confirmed_and_unknown_note_fails(run, capsys, monkeypatch):
    run("note", "add", "1", "temporary")
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    assert run("note", "delete", "1") == 0

    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("prompted"))
    capsys.readouterr()
    assert run("note", "delete", "9") == 1
    assert "Note 9 not found." in capsys.readouterr().out


def test_ids_are_validated(run):
    with pytest.raises(SystemExit):
        run("note", "add", "0", "x")
    with pytest.raises(SystemExit):
        run("note", "add", "1")
