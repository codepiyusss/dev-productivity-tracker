import pytest

from src.database import Database
from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    for title in ("Design", "Build", "Ship"):
        _run("add", title)
    _run("depend", "add", "2", "1")
    _run("depend", "add", "3", "2")
    _run.db = str(tmp_path / "t.db")
    return _run


def completed(run, task_id):
    return Database(run.db).get_task(task_id).completed


def test_blocked_task_cannot_be_completed(run, capsys):
    capsys.readouterr()

    assert run("complete", "2") == 1

    output = capsys.readouterr().out
    assert "Task 2 is waiting on unfinished tasks:" in output
    assert "  [1] Design" in output
    assert "use --force" in output
    assert completed(run, 2) is False


def test_force_completes_it_anyway(run, capsys):
    capsys.readouterr()

    assert run("complete", "2", "--force") == 0

    assert "Task completed." in capsys.readouterr().out
    assert completed(run, 2) is True


def test_unblocked_tasks_complete_normally(run, capsys):
    capsys.readouterr()

    assert run("complete", "1") == 0
    assert completed(run, 1) is True


def test_completing_blockers_in_order_works_without_force(run, capsys):
    assert run("complete", "1") == 0
    assert run("complete", "2") == 0
    assert run("complete", "3") == 0


def test_all_unfinished_blockers_are_listed(run, capsys):
    run("add", "Extra")
    run("depend", "add", "3", "4")
    capsys.readouterr()

    run("complete", "3")

    output = capsys.readouterr().out
    assert "[2] Build" in output and "[4] Extra" in output


def test_a_refused_completion_does_not_stop_the_timer(run, capsys):
    run("timer", "start", "2")
    capsys.readouterr()

    assert run("complete", "2") == 1

    run("timer", "status")
    assert "task 2" in capsys.readouterr().out


def test_completing_an_already_completed_task_is_not_refused(run, capsys):
    run("complete", "2", "--force")
    capsys.readouterr()

    assert run("complete", "2") == 0


def test_missing_task_still_reports_not_found(run, capsys):
    capsys.readouterr()

    assert run("complete", "9") == 1
    assert "Task not found." in capsys.readouterr().out
