import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    _run("add", "Write docs")
    _run("add", "Other task")
    return _run


def test_completing_the_timed_task_stops_its_timer(run, capsys):
    run("timer", "start", "1")
    capsys.readouterr()

    assert run("complete", "1") == 0

    output = capsys.readouterr().out
    assert "Task completed." in output
    assert "Timer stopped automatically (" in output

    run("timer", "status")
    assert "No timer is running." in capsys.readouterr().out


def test_the_stopped_time_is_recorded(run, capsys):
    run("timer", "start", "1")
    run("complete", "1")
    capsys.readouterr()

    run("timer", "list", "--task", "1")

    assert "task 1: Write docs" in capsys.readouterr().out


def test_completing_another_task_leaves_the_timer_running(run, capsys):
    run("timer", "start", "1")
    capsys.readouterr()

    run("complete", "2")

    assert "Timer stopped automatically" not in capsys.readouterr().out
    run("timer", "status")
    assert "task 1" in capsys.readouterr().out


def test_completing_without_a_timer_is_unchanged(run, capsys):
    run("complete", "1")

    assert "Timer stopped automatically" not in capsys.readouterr().out


def test_missing_task_does_not_touch_the_timer(run, capsys):
    run("timer", "start", "1")
    capsys.readouterr()

    assert run("complete", "99") == 1

    run("timer", "status")
    assert "task 1" in capsys.readouterr().out
