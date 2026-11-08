from datetime import datetime, timedelta

import pytest

from src.database import Database
from src.models.task import Task
from src.timetracking import TimeTracker, entry_seconds

START = datetime(2026, 11, 10, 9, 0, 0)


@pytest.fixture
def tracker():
    database = Database(":memory:")
    database.add_task(Task("First"))
    database.add_task(Task("Second"))
    return TimeTracker(database)


def test_stop_finishes_the_entry_and_reports_duration(tracker):
    tracker.start(1, START)

    entry = tracker.stop(START + timedelta(minutes=45, seconds=30))

    assert entry["task_id"] == 1
    assert entry["ended_at"] == "2026-11-10T09:45:30"
    assert entry["seconds"] == 2730
    assert tracker.database.get_running_entry() is None
    assert tracker.database.get_time_entries()[0]["ended_at"] == "2026-11-10T09:45:30"


def test_stop_without_a_running_timer_is_rejected(tracker):
    with pytest.raises(ValueError, match="No timer is running"):
        tracker.stop(START)


def test_stopping_twice_is_rejected(tracker):
    tracker.start(1, START)
    tracker.stop(START + timedelta(minutes=5))

    with pytest.raises(ValueError, match="No timer is running"):
        tracker.stop(START + timedelta(minutes=6))


def test_a_new_timer_can_start_after_stopping(tracker):
    tracker.start(1, START)
    tracker.stop(START + timedelta(minutes=5))

    tracker.start(2, START + timedelta(minutes=10))

    assert tracker.database.get_running_entry()["task_id"] == 2


def test_clock_going_backwards_never_gives_negative_time(tracker):
    tracker.start(1, START)

    entry = tracker.stop(START - timedelta(minutes=30))

    assert entry["seconds"] == 0
    assert entry["ended_at"] == entry["started_at"]


def test_entry_seconds_for_finished_and_running_entries():
    finished = {"started_at": "2026-11-10T09:00:00", "ended_at": "2026-11-10T10:30:00"}
    running = {"started_at": "2026-11-10T09:00:00", "ended_at": None}

    assert entry_seconds(finished) == 5400
    assert entry_seconds(running, now=datetime(2026, 11, 10, 9, 20, 0)) == 1200
    assert entry_seconds(running, now=datetime(2026, 11, 10, 8, 0, 0)) == 0
