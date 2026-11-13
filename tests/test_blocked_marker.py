from datetime import date

import pytest

from src.main import format_task_line, main
from src.models.task import Task

TODAY = date(2026, 11, 10)


def line(**kwargs):
    blocked_by = kwargs.pop("blocked_by", None)
    return format_task_line(
        Task("Ship", task_id=3, **kwargs), TODAY, blocked_by=blocked_by
    )


def test_no_marker_without_blockers():
    assert line() == "[3] Ship | medium | general | Pending"


def test_marker_lists_blocking_task_ids():
    assert line(blocked_by=[1, 2]).endswith("| Pending | BLOCKED by 1,2")


def test_marker_sits_before_the_tags_and_after_due_and_repeat():
    text = line(
        due_date="2026-12-01", recurrence="weekly", tags=["work"], blocked_by=[7]
    )

    assert text.endswith("| due 2026-12-01 | repeats weekly | BLOCKED by 7 | #work")


def test_completed_tasks_never_show_the_marker():
    assert "BLOCKED" not in line(completed=True, blocked_by=[1])


def test_empty_blocker_list_shows_nothing():
    assert "BLOCKED" not in line(blocked_by=[])


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    for title in ("Design", "Build"):
        _run("add", title)
    _run("depend", "add", "2", "1")
    return _run


def test_list_marks_blocked_tasks(run, capsys):
    capsys.readouterr()

    run("list")

    output = capsys.readouterr().out
    assert "[2] Build | medium | general | Pending | BLOCKED by 1" in output
    assert "[1] Design | medium | general | Pending\n" in output


def test_marker_disappears_when_the_blocker_is_completed(run, capsys):
    run("complete", "1")
    capsys.readouterr()

    run("list")

    assert "BLOCKED" not in capsys.readouterr().out
