from datetime import datetime, timedelta

import pytest

from src.database import Database
from src.models.task import Task
from src.timetracking import TimeTracker

START = datetime(2026, 11, 10, 9, 0, 0)


@pytest.fixture
def tracker():
    database = Database(":memory:")
    database.add_task(Task("First"))
    database.add_task(Task("Second"))
    return TimeTracker(database)


def test_total_is_zero_without_entries(tracker):
    assert tracker.total_seconds(1, START) == 0


def test_total_adds_up_all_finished_entries(tracker):
    tracker.start(1, START)
    tracker.stop(START + timedelta(minutes=30))
    tracker.log_manual(1, 1800, now=START + timedelta(days=1))

    assert tracker.total_seconds(1, START + timedelta(days=2)) == 3600


def test_total_includes_a_running_timer_up_to_now(tracker):
    tracker.start(1, START)

    assert tracker.total_seconds(1, START + timedelta(minutes=20)) == 1200


def test_totals_are_kept_per_task(tracker):
    tracker.log_manual(1, 600, now=START)
    tracker.log_manual(2, 1500, now=START)

    assert tracker.total_seconds(1, START) == 600
    assert tracker.total_seconds(2, START) == 1500


def test_total_for_unknown_task_is_zero(tracker):
    assert tracker.total_seconds(99, START) == 0
