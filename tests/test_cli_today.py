from datetime import date, timedelta

import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    return _run


def test_today_on_an_empty_database(run, capsys):
    assert run("today") == 0

    output = capsys.readouterr().out
    assert output.startswith(f"Today: {date.today().isoformat()} (")
    assert "Nothing is due" in output
    assert "Completed today: 0" in output


def test_today_shows_overdue_due_today_and_upcoming(run, capsys):
    today = date.today()
    run("add", "Late task", "--due-date", (today - timedelta(days=2)).isoformat())
    run("add", "Today task", "--due-date", today.isoformat())
    run("add", "Soon task", "--due-date", (today + timedelta(days=1)).isoformat())
    run("add", "Far task", "--due-date", (today + timedelta(days=30)).isoformat())
    capsys.readouterr()

    run("today")

    output = capsys.readouterr().out
    assert "Overdue (1):" in output and "Late task" in output
    assert "Due today (1):" in output and "Today task" in output
    assert "Coming up (next 3 days) (1):" in output and "Soon task" in output
    assert "Far task" not in output
    assert "Pending: 4 (4 ready to start)" in output


def test_today_reflects_completions_timer_and_goals(run, capsys):
    run("add", "Write docs")
    run("add", "Ship it")
    run("goal", "set", "daily", "2")
    run("complete", "1")
    run("timer", "start", "2")
    capsys.readouterr()

    run("today")

    output = capsys.readouterr().out
    assert "Timer running on task 2: Ship it" in output
    assert "Daily goal:" in output and "1/2" in output
    assert "Completed today: 1" in output
    assert "Streak: 1 day" in output


def test_today_counts_blocked_tasks(run, capsys):
    run("add", "A")
    run("add", "B")
    run("depend", "add", "2", "1")
    capsys.readouterr()

    run("today")

    assert "Pending: 2 (1 ready to start, 1 blocked)" in capsys.readouterr().out
