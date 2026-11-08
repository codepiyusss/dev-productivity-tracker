import json
from datetime import date, datetime

import pytest

from src.database import Database
from src.models.task import Task
from src.timetracking import TimeTracker

NOW = datetime(2026, 11, 10, 18, 0, 0)


@pytest.fixture
def tracker():
    database = Database(":memory:")
    database.add_task(Task("Write docs", category="work"))
    database.add_task(Task("Read book", category="home"))
    database.add_task(Task("Fix bug", category="work"))
    return TimeTracker(database)


def log(tracker, task_id, minutes, day):
    tracker.log_manual(task_id, minutes * 60, day=day, now=NOW)


def test_empty_summary_lists_every_day_with_zero(tracker):
    summary = tracker.get_summary(days=3, now=NOW)

    assert summary["total_seconds"] == 0
    assert summary["entry_count"] == 0
    assert [d["date"] for d in summary["by_day"]] == [
        "2026-11-08", "2026-11-09", "2026-11-10"
    ]
    assert summary["by_task"] == [] and summary["by_category"] == []


def test_totals_by_day_task_and_category(tracker):
    log(tracker, 1, 60, date(2026, 11, 10))
    log(tracker, 1, 30, date(2026, 11, 9))
    log(tracker, 2, 45, date(2026, 11, 9))
    log(tracker, 3, 15, date(2026, 11, 10))

    summary = tracker.get_summary(days=7, now=NOW)

    assert summary["total_seconds"] == (60 + 30 + 45 + 15) * 60
    assert summary["entry_count"] == 4
    assert {d["date"]: d["seconds"] for d in summary["by_day"]}["2026-11-09"] == 75 * 60
    assert [t["title"] for t in summary["by_task"]] == [
        "Write docs", "Read book", "Fix bug"
    ]
    assert summary["by_category"] == [
        {"category": "work", "seconds": 105 * 60},
        {"category": "home", "seconds": 45 * 60},
    ]


def test_entries_outside_the_window_are_excluded(tracker):
    log(tracker, 1, 60, date(2026, 11, 1))
    log(tracker, 1, 30, date(2026, 11, 9))

    summary = tracker.get_summary(days=2, now=NOW)

    assert summary["total_seconds"] == 30 * 60
    assert summary["entry_count"] == 1


def test_running_timer_is_included_up_to_now(tracker):
    tracker.start(1, datetime(2026, 11, 10, 17, 0, 0))

    summary = tracker.get_summary(days=1, now=NOW)

    assert summary["total_seconds"] == 3600
    assert summary["by_task"][0]["seconds"] == 3600


def test_ties_are_ordered_by_task_id(tracker):
    log(tracker, 3, 30, date(2026, 11, 10))
    log(tracker, 1, 30, date(2026, 11, 10))

    titles = [t["title"] for t in tracker.get_summary(days=1, now=NOW)["by_task"]]

    assert titles == ["Write docs", "Fix bug"]


def test_days_must_be_positive(tracker):
    with pytest.raises(ValueError):
        tracker.get_summary(days=0, now=NOW)


def test_summary_is_json_serializable(tracker):
    log(tracker, 1, 30, date(2026, 11, 10))

    assert json.loads(json.dumps(tracker.get_summary(days=3, now=NOW)))["entry_count"] == 1
