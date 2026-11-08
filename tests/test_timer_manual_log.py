from datetime import date, datetime

import pytest

from src.database import Database
from src.models.task import Task
from src.timetracking import TimeTracker, entry_seconds

NOW = datetime(2026, 11, 10, 15, 30, 0)


@pytest.fixture
def tracker():
    database = Database(":memory:")
    database.add_task(Task("Write docs"))
    return TimeTracker(database)


def test_log_without_a_date_ends_now(tracker):
    entry = tracker.log_manual(1, 5400, now=NOW)

    assert entry["started_at"] == "2026-11-10T14:00:00"
    assert entry["ended_at"] == "2026-11-10T15:30:00"
    assert entry_seconds(entry) == 5400


def test_log_for_today_behaves_like_no_date(tracker):
    entry = tracker.log_manual(1, 600, day=date(2026, 11, 10), now=NOW)

    assert entry["ended_at"] == "2026-11-10T15:30:00"


def test_log_for_an_earlier_day_is_placed_at_nine(tracker):
    entry = tracker.log_manual(1, 7200, day=date(2026, 11, 8), now=NOW)

    assert entry["started_at"] == "2026-11-08T09:00:00"
    assert entry["ended_at"] == "2026-11-08T11:00:00"


def test_manual_entries_are_finished_and_never_block_the_timer(tracker):
    tracker.log_manual(1, 600, now=NOW)

    assert tracker.database.get_running_entry() is None
    tracker.start(1, NOW)


def test_future_dates_are_rejected(tracker):
    with pytest.raises(ValueError, match="future"):
        tracker.log_manual(1, 600, day=date(2026, 11, 11), now=NOW)

    assert tracker.database.get_time_entries() == []


def test_unknown_task_is_rejected(tracker):
    with pytest.raises(ValueError, match="Task 7 not found"):
        tracker.log_manual(7, 600, now=NOW)


@pytest.mark.parametrize("seconds", [0, -60])
def test_non_positive_duration_is_rejected(tracker, seconds):
    with pytest.raises(ValueError, match="greater than zero"):
        tracker.log_manual(1, seconds, now=NOW)


def test_logging_works_while_a_timer_is_running(tracker):
    tracker.start(1, NOW)

    tracker.log_manual(1, 600, day=date(2026, 11, 9), now=NOW)

    assert len(tracker.database.get_time_entries()) == 2
    assert tracker.database.get_running_entry() is not None
