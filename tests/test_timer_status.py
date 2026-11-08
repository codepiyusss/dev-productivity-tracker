from datetime import datetime, timedelta

import pytest

from src.database import Database
from src.models.task import Task
from src.timetracking import STALE_AFTER_SECONDS, TimeTracker

START = datetime(2026, 11, 10, 9, 0, 0)


@pytest.fixture
def tracker():
    database = Database(":memory:")
    database.add_task(Task("Write docs"))
    return TimeTracker(database)


def test_status_is_none_when_idle(tracker):
    assert tracker.status(START) is None


def test_status_reports_task_and_elapsed_time(tracker):
    tracker.start(1, START)

    status = tracker.status(START + timedelta(minutes=25))

    assert status["task_id"] == 1
    assert status["title"] == "Write docs"
    assert status["seconds"] == 1500
    assert status["stale"] is False


def test_status_flags_forgotten_timers(tracker):
    tracker.start(1, START)

    just_under = tracker.status(START + timedelta(seconds=STALE_AFTER_SECONDS - 1))
    at_limit = tracker.status(START + timedelta(seconds=STALE_AFTER_SECONDS))

    assert just_under["stale"] is False
    assert at_limit["stale"] is True


def test_status_does_not_change_the_timer(tracker):
    tracker.start(1, START)

    tracker.status(START + timedelta(hours=1))

    assert tracker.database.get_running_entry()["ended_at"] is None


def test_status_is_none_after_stopping(tracker):
    tracker.start(1, START)
    tracker.stop(START + timedelta(minutes=5))

    assert tracker.status(START + timedelta(minutes=6)) is None
