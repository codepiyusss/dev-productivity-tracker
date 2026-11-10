import pytest

from src.database import Database
from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv]) or 0

    _run.db = str(tmp_path / "t.db")
    return _run


def test_completing_a_repeating_task_announces_the_next_one(run, capsys):
    run("add", "Standup", "--due-date", "2999-01-01", "--repeat", "daily", "--tags", "team")
    capsys.readouterr()

    assert run("complete", "1") == 0

    output = capsys.readouterr().out
    assert "Task completed." in output
    assert "Next occurrence created: [2] Standup (due 2999-01-02)" in output

    tasks = sorted(Database(run.db).get_all_tasks(), key=lambda t: t.task_id)
    assert [(t.task_id, t.completed, t.due_date, t.tags) for t in tasks] == [
        (1, True, "2999-01-01", ["team"]),
        (2, False, "2999-01-02", ["team"]),
    ]


def test_completing_a_plain_task_says_nothing_extra(run, capsys):
    run("add", "One-off", "--due-date", "2999-01-01")
    capsys.readouterr()

    run("complete", "1")

    assert "Next occurrence" not in capsys.readouterr().out
    assert len(Database(run.db).get_all_tasks()) == 1


def test_completing_the_same_task_twice_does_not_repeat_twice(run, capsys):
    run("add", "Standup", "--due-date", "2999-01-01", "--repeat", "weekly")
    run("complete", "1")
    capsys.readouterr()

    run("complete", "1")

    assert "Next occurrence" not in capsys.readouterr().out
    assert len(Database(run.db).get_all_tasks()) == 2


def test_missing_task_still_fails(run, capsys):
    assert run("complete", "9") == 1
    assert "Task not found." in capsys.readouterr().out


def test_goals_streak_and_timer_messages_still_appear(run, capsys):
    run("add", "Standup", "--due-date", "2999-01-01", "--repeat", "daily")
    run("goal", "set", "daily", "2")
    run("timer", "start", "1")
    capsys.readouterr()

    run("complete", "1")

    output = capsys.readouterr().out
    assert "Timer stopped automatically" in output
    assert "Daily goal:" in output
    assert "Streak: 1 day" in output
