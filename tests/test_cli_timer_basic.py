from datetime import datetime, timedelta

from src.main import main


def run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "t.db"), *argv])


def setup_task(tmp_path, capsys, title="Write docs"):
    run(tmp_path, "add", title)
    capsys.readouterr()


def test_start_status_stop_flow(tmp_path, capsys):
    setup_task(tmp_path, capsys)

    assert run(tmp_path, "timer", "start", "1") == 0
    assert "Timer started on task 1: Write docs" in capsys.readouterr().out

    assert run(tmp_path, "timer", "status") == 0
    assert "Timer running on task 1: Write docs (" in capsys.readouterr().out

    assert run(tmp_path, "timer", "stop") == 0
    output = capsys.readouterr().out
    assert "Stopped timer on task 1: Write docs" in output
    assert "Total on this task:" in output

    run(tmp_path, "timer", "status")
    assert "No timer is running." in capsys.readouterr().out


def test_start_unknown_task_fails(tmp_path, capsys):
    assert run(tmp_path, "timer", "start", "9") == 1
    assert "Task 9 not found." in capsys.readouterr().out


def test_second_start_fails_and_keeps_the_first_timer(tmp_path, capsys):
    setup_task(tmp_path, capsys)
    run(tmp_path, "add", "Other")
    run(tmp_path, "timer", "start", "1")
    capsys.readouterr()

    assert run(tmp_path, "timer", "start", "2") == 1
    assert "already running on task 1" in capsys.readouterr().out

    run(tmp_path, "timer", "status")
    assert "task 1" in capsys.readouterr().out


def test_stop_without_timer_fails(tmp_path, capsys):
    assert run(tmp_path, "timer", "stop") == 1
    assert "No timer is running." in capsys.readouterr().out


def test_status_warns_about_forgotten_timer(tmp_path, capsys):
    setup_task(tmp_path, capsys)
    run(tmp_path, "timer", "start", "1")
    capsys.readouterr()

    # Pretend the timer was started yesterday.
    import sqlite3
    old = (datetime.now() - timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%S")
    with sqlite3.connect(str(tmp_path / "t.db")) as connection:
        connection.execute("UPDATE time_entries SET started_at = ?", (old,))

    run(tmp_path, "timer", "status")

    output = capsys.readouterr().out
    assert "20h" in output
    assert "Warning" in output


def test_invalid_task_id_is_rejected_at_parse_time(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        run(tmp_path, "timer", "start", "0")
