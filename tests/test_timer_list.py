from datetime import datetime

import pytest

from src.database import Database
from src.main import format_time_entry, main
from src.models.task import Task
from src.timetracking import TimeTracker

NOW = datetime(2026, 11, 10, 18, 0, 0)


@pytest.fixture
def tracker():
    database = Database(":memory:")
    database.add_task(Task("Write docs"))
    database.add_task(Task("Read book"))
    return TimeTracker(database)


def test_list_entries_returns_titles_and_seconds(tracker):
    tracker.log_manual(1, 1800, now=NOW)

    entry = tracker.list_entries(now=NOW)[0]

    assert entry["title"] == "Write docs"
    assert entry["seconds"] == 1800


def test_list_entries_limits_by_days_and_task(tracker):
    tracker.log_manual(1, 600, day=datetime(2026, 11, 1).date(), now=NOW)
    tracker.log_manual(1, 600, day=datetime(2026, 11, 9).date(), now=NOW)
    tracker.log_manual(2, 600, day=datetime(2026, 11, 10).date(), now=NOW)

    assert len(tracker.list_entries(days=7, now=NOW)) == 2
    assert len(tracker.list_entries(days=30, now=NOW)) == 3
    assert [e["task_id"] for e in tracker.list_entries(task_id=2, days=30, now=NOW)] == [2]


def test_list_entries_includes_running_timer(tracker):
    tracker.start(1, datetime(2026, 11, 10, 17, 0, 0))

    entry = tracker.list_entries(now=NOW)[0]

    assert entry["ended_at"] is None
    assert entry["seconds"] == 3600


def test_list_entries_validates_days(tracker):
    with pytest.raises(ValueError):
        tracker.list_entries(days=0, now=NOW)


def test_format_finished_and_running_entries():
    finished = {
        "entry_id": 4, "task_id": 1, "title": "Write docs", "seconds": 2700,
        "started_at": "2026-11-10T09:00:00", "ended_at": "2026-11-10T09:45:00",
    }
    running = {**finished, "ended_at": None, "seconds": 120}

    assert format_time_entry(finished) == (
        "#4 2026-11-10 09:00-09:45 | 45m | task 1: Write docs"
    )
    assert format_time_entry(running) == (
        "#4 2026-11-10 09:00-now | 2m | task 1: Write docs (running)"
    )


def test_cli_list_shows_entries_or_a_helpful_message(tmp_path, capsys):
    def run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    run("add", "Write docs")
    run("timer", "list")
    assert "No time entries in the last 7 day(s)." in capsys.readouterr().out

    run("timer", "log", "1", "30m")
    capsys.readouterr()

    assert run("timer", "list", "--task", "1", "--days", "3") == 0
    output = capsys.readouterr().out
    assert "30m | task 1: Write docs" in output
