import pytest

from src.main import format_task_details, main
from src.models.task import Task


def task():
    return Task("Write docs", task_id=1, created_at="2026-11-10T09:00:00")


def note(number, text, stamp="2026-11-10T09:30:00"):
    return {"note_id": number, "task_id": 1, "text": text, "created_at": stamp}


def test_details_omit_notes_when_there_are_none():
    assert "Notes" not in format_task_details(task())
    assert "Notes" not in format_task_details(task(), notes=[])


def test_details_list_notes_after_the_description():
    lines = format_task_details(
        task(), notes=[note(1, "first"), note(2, "second\nline two")]
    ).splitlines()

    index = lines.index("  Notes (2):")
    assert lines[index - 1].startswith("  Description:")
    assert lines[index + 1] == "    #1 2026-11-10 09:30  first"
    assert lines[index + 2] == "    #2 2026-11-10 09:30  second"
    assert lines[index + 3].endswith("line two") and lines[index + 3].startswith(" " * 20)


def test_other_detail_lines_still_come_before_the_description():
    lines = format_task_details(
        task(), tracked_seconds=600, notes=[note(1, "x")]
    ).splitlines()

    assert lines.index("  Time spent:  10m") == lines.index("  Notes (1):") - 2


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    _run("add", "Write docs")
    _run("add", "Other task")
    return _run


def test_show_displays_that_tasks_notes_only(run, capsys):
    run("note", "add", "1", "Remember the examples")
    run("note", "add", "2", "Unrelated")
    capsys.readouterr()

    run("show", "1")

    output = capsys.readouterr().out
    assert "Notes (1):" in output and "Remember the examples" in output
    assert "Unrelated" not in output


def test_show_without_notes_has_no_notes_section(run, capsys):
    capsys.readouterr()

    run("show", "1")

    assert "Notes" not in capsys.readouterr().out
