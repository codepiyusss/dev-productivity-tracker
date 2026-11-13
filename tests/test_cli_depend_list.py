import pytest

from src.main import format_dependencies, main
from src.models.task import Task


def task(number, title, done=False):
    return Task(title, task_id=number, completed=done)


def test_format_with_no_dependencies():
    assert format_dependencies(task(1, "Solo"), [], []) == (
        "Task 1: Solo\n  No dependencies."
    )


def test_format_shows_both_directions_with_status():
    text = format_dependencies(
        task(2, "Build"),
        [task(1, "Design", done=True)],
        [task(3, "Ship"), task(4, "Announce", done=True)],
    )

    assert text.splitlines() == [
        "Task 2: Build",
        "Waits for:",
        "  [1] Design (done)",
        "Is needed by:",
        "  [3] Ship (pending)",
        "  [4] Announce (done)",
    ]


def test_format_only_shows_sections_that_exist():
    text = format_dependencies(task(3, "Ship"), [task(2, "Build")], [])

    assert "Waits for:" in text
    assert "Is needed by:" not in text


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    for title in ("Design", "Build", "Ship"):
        _run("add", title)
    _run("depend", "add", "2", "1")
    _run("depend", "add", "3", "2")
    return _run


def test_depend_list_for_a_middle_task(run, capsys):
    capsys.readouterr()

    assert run("depend", "list", "2") == 0

    output = capsys.readouterr().out
    assert "Waits for:\n  [1] Design (pending)" in output
    assert "Is needed by:\n  [3] Ship (pending)" in output


def test_completed_tasks_still_appear_with_their_status(run, capsys):
    run("complete", "1")
    capsys.readouterr()

    run("depend", "list", "2")

    assert "[1] Design (done)" in capsys.readouterr().out


def test_depend_list_unknown_task(run, capsys):
    capsys.readouterr()

    assert run("depend", "list", "9") == 1
    assert "Task not found." in capsys.readouterr().out
