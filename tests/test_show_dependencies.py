import pytest

from src.main import format_task_details, main
from src.models.task import Task


def task():
    return Task("Build", task_id=2, created_at="2026-11-10T09:00:00")


def other(number, title):
    return Task(title, task_id=number)


def test_details_omit_dependency_lines_when_there_are_none():
    text = format_task_details(task())

    assert "Waits for" not in text and "Needed by" not in text


def test_details_list_blockers_and_dependents():
    text = format_task_details(
        task(),
        waits_for=[other(1, "Design"), other(4, "Review")],
        needed_by=[other(3, "Ship")],
    )

    assert "  Waits for:   [1] Design, [4] Review" in text
    assert "  Needed by:   [3] Ship" in text


def test_dependency_lines_come_before_time_spent_and_description():
    lines = format_task_details(
        task(), tracked_seconds=600, waits_for=[other(1, "Design")]
    ).splitlines()

    assert lines.index("  Waits for:   [1] Design") < lines.index("  Time spent:  10m")
    assert lines[-2] == "  Time spent:  10m"
    assert lines[-1].startswith("  Description:")


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    for title in ("Design", "Build", "Ship"):
        _run("add", title)
    _run("depend", "add", "2", "1")
    _run("depend", "add", "3", "2")
    return _run


def test_show_displays_both_directions(run, capsys):
    capsys.readouterr()

    run("show", "2")

    output = capsys.readouterr().out
    assert "Waits for:   [1] Design" in output
    assert "Needed by:   [3] Ship" in output


def test_show_only_lists_unfinished_blockers(run, capsys):
    run("complete", "1")
    capsys.readouterr()

    run("show", "2")

    assert "Waits for" not in capsys.readouterr().out


def test_show_for_an_independent_task_has_no_dependency_lines(run, capsys):
    run("add", "Solo")
    capsys.readouterr()

    run("show", "4")

    output = capsys.readouterr().out
    assert "Waits for" not in output and "Needed by" not in output
