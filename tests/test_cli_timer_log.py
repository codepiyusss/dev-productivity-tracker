import pytest

from src.main import duration_seconds, main


def run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "t.db"), *argv])


@pytest.fixture
def task(tmp_path, capsys):
    run(tmp_path, "add", "Write docs")
    capsys.readouterr()


def test_log_adds_time_and_reports_total(tmp_path, task, capsys):
    assert run(tmp_path, "timer", "log", "1", "1h30m") == 0
    assert "Logged 1h 30m on task 1: Write docs" in capsys.readouterr().out

    run(tmp_path, "timer", "log", "1", "45")
    output = capsys.readouterr().out
    assert "Logged 45m" in output
    assert "Total on this task: 2h 15m" in output


def test_log_accepts_a_past_date(tmp_path, task, capsys):
    assert run(tmp_path, "timer", "log", "1", "30m", "--date", "2026-01-05") == 0

    from src.database import Database
    entries = Database(str(tmp_path / "t.db")).get_time_entries()
    assert entries[0]["started_at"] == "2026-01-05T09:00:00"


def test_log_rejects_future_date(tmp_path, task, capsys):
    assert run(tmp_path, "timer", "log", "1", "30m", "--date", "2999-01-01") == 1
    assert "future" in capsys.readouterr().out


def test_log_unknown_task(tmp_path, capsys):
    assert run(tmp_path, "timer", "log", "5", "30m") == 1
    assert "Task 5 not found." in capsys.readouterr().out


@pytest.mark.parametrize("duration", ["0", "abc", "25h", "-5"])
def test_log_rejects_bad_durations_at_parse_time(tmp_path, task, capsys, duration):
    with pytest.raises(SystemExit) as exit_info:
        run(tmp_path, "timer", "log", "1", duration)

    assert exit_info.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_duration_seconds_helper():
    assert duration_seconds("1:30") == 5400

    import argparse
    with pytest.raises(argparse.ArgumentTypeError, match="1h30m"):
        duration_seconds("nope")
