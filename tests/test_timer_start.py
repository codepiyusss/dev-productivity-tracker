from datetime import datetime

import pytest

from src.database import Database
from src.models.task import Task
from src.timetracking import TimeTracker

NOW = datetime(2026, 11, 10, 9, 0, 0)


@pytest.fixture
def tracker():
    database = Database(":memory:")
    database.add_task(Task("First"))
    database.add_task(Task("Second"))
    return TimeTracker(database)


def test_start_creates_a_running_entry(tracker):
    entry = tracker.start(1, NOW)

    assert entry["task_id"] == 1
    assert entry["started_at"] == "2026-11-10T09:00:00"
    assert entry["ended_at"] is None
    assert tracker.database.get_running_entry()["entry_id"] == entry["entry_id"]


def test_start_defaults_to_the_current_time(tracker):
    before = datetime.now().replace(microsecond=0)

    entry = tracker.start(1)

    started = datetime.strptime(entry["started_at"], "%Y-%m-%dT%H:%M:%S")
    assert before <= started <= datetime.now()


def test_start_unknown_task_is_rejected(tracker):
    with pytest.raises(ValueError, match="Task 99 not found"):
        tracker.start(99, NOW)

    assert tracker.database.get_time_entries() == []


def test_second_timer_is_rejected_and_names_the_running_task(tracker):
    tracker.start(1, NOW)

    with pytest.raises(ValueError, match="already running on task 1"):
        tracker.start(2, NOW)

    assert len(tracker.database.get_time_entries()) == 1


def test_starting_the_same_task_twice_is_also_rejected(tracker):
    tracker.start(1, NOW)

    with pytest.raises(ValueError, match="already running"):
        tracker.start(1, NOW)
