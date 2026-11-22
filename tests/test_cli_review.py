import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    return _run


def test_review_on_an_empty_database(run, capsys):
    assert run("review") == 0

    output = capsys.readouterr().out
    assert "(7 days)" in output
    assert "Completed: 0 tasks (created: 0)" in output
    assert "Time tracked: none" in output


def test_review_reflects_real_activity(run, capsys):
    run("add", "Write docs", "--category", "work")
    run("add", "Fix bug")
    run("goal", "set", "daily", "1")
    run("timer", "log", "1", "1h30m")
    run("complete", "1")
    run("journal", "add", "--achievements", "Good day")
    capsys.readouterr()

    assert run("review") == 0

    output = capsys.readouterr().out
    assert "Completed: 1 task (created: 2)" in output
    assert "Active days: 1 of 7" in output
    assert "Busiest day:" in output and "(1 task)" in output
    assert "Time tracked: 1h 30m (work 1h 30m)" in output
    assert "Daily goal met on 1 of 7 days (target: 1 per day)" in output
    assert "Journal: written on 1 day" in output
    assert "Streak: 1 day" in output
    assert "[1] Write docs" in output


def test_days_option_changes_the_window(run, capsys):
    capsys.readouterr()

    run("review", "--days", "1")

    output = capsys.readouterr().out
    assert "(1 day)" in output and "Active days: 0 of 1" in output


def test_days_must_be_positive(run):
    with pytest.raises(SystemExit):
        run("review", "--days", "0")


def test_review_does_not_change_anything(run, capsys):
    run("add", "Write docs")
    run("review")
    capsys.readouterr()

    run("list")

    assert capsys.readouterr().out.count("[1]") == 1
