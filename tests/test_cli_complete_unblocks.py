import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    for title in ("Design", "Build", "Test", "Ship"):
        _run("add", title)
    _run("depend", "add", "2", "1")     # Build waits for Design
    _run("depend", "add", "3", "1")     # Test waits for Design and Build
    _run("depend", "add", "3", "2")
    return _run


def test_completing_a_blocker_lists_the_tasks_it_frees(run, capsys):
    capsys.readouterr()

    assert run("complete", "1") == 0

    output = capsys.readouterr().out
    assert "Task completed." in output
    assert "Now ready to start:\n  [2] Build" in output


def test_a_task_with_another_open_blocker_is_not_announced(run, capsys):
    capsys.readouterr()

    run("complete", "1")

    assert "[3] Test" not in capsys.readouterr().out


def test_the_last_blocker_frees_the_waiting_task(run, capsys):
    run("complete", "1")
    capsys.readouterr()

    run("complete", "2")

    assert "Now ready to start:\n  [3] Test" in capsys.readouterr().out


def test_nothing_is_announced_when_nothing_is_freed(run, capsys):
    capsys.readouterr()

    run("complete", "4")

    assert "Now ready" not in capsys.readouterr().out


def test_forced_completion_of_a_blocker_still_frees_dependents_correctly(run, capsys):
    run("complete", "2", "--force")          # Build done while Design is open
    capsys.readouterr()

    run("complete", "1")

    output = capsys.readouterr().out
    assert "[3] Test" in output              # both its blockers are done now


def test_goal_streak_and_freed_messages_all_appear(run, capsys):
    run("goal", "set", "daily", "2")
    capsys.readouterr()

    run("complete", "1")

    output = capsys.readouterr().out
    assert "Daily goal:" in output
    assert "Streak: 1 day" in output
    assert "Now ready to start:" in output
