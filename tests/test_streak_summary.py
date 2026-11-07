import json
from datetime import date

import pytest

from src.database import Database
from src.models.task import Task
from src.streaks import StreakTracker

TODAY = date(2026, 11, 12)


def build(completions, daily_target=None):
    database = Database(":memory:")
    if daily_target:
        database.set_goal("daily", daily_target)
    for day, count in completions.items():
        for number in range(count):
            database.add_task(Task(
                f"{day}-{number}", completed=True,
                completed_at=f"{day}T1{number}:00:00"
            ))
    return StreakTracker(database)


def test_empty_summary():
    summary = build({}).get_summary(TODAY, days=3)

    assert summary["current"] == 0
    assert summary["longest"] == 0
    assert summary["at_risk"] is False
    assert summary["total_active_days"] == 0
    assert summary["goal_streak"] is None
    assert summary["last_active"] is None
    assert [d["completed"] for d in summary["recent"]] == [0, 0, 0]


def test_summary_reports_current_and_longest():
    tracker = build({
        "2026-10-01": 1, "2026-10-02": 1, "2026-10-03": 1, "2026-10-04": 1,
        "2026-11-11": 1, "2026-11-12": 2,
    })

    summary = tracker.get_summary(TODAY)

    assert summary["current"] == 2
    assert summary["active_today"] is True
    assert summary["longest"] == 4
    assert (summary["longest_start"], summary["longest_end"]) == (
        "2026-10-01", "2026-10-04"
    )
    assert summary["total_active_days"] == 6


def test_recent_is_oldest_first_and_ends_today():
    tracker = build({"2026-11-10": 2, "2026-11-12": 1})

    recent = tracker.get_summary(TODAY, days=4)["recent"]

    assert [d["date"] for d in recent] == [
        "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"
    ]
    assert [d["completed"] for d in recent] == [0, 2, 0, 1]


def test_at_risk_when_streak_alive_but_nothing_done_today():
    summary = build({"2026-11-10": 1, "2026-11-11": 1}).get_summary(TODAY)

    assert summary["current"] == 2
    assert summary["at_risk"] is True
    assert summary["last_active"] == "2026-11-11"


def test_goal_streak_included_when_goal_is_set():
    summary = build({"2026-11-11": 2, "2026-11-12": 2}, daily_target=2).get_summary(TODAY)

    assert summary["goal_streak"] == 2
    assert summary["daily_target"] == 2


def test_summary_is_json_serializable():
    summary = build({"2026-11-12": 1}, daily_target=1).get_summary(TODAY)

    assert json.loads(json.dumps(summary))["current"] == 1


def test_days_must_be_positive():
    with pytest.raises(ValueError):
        build({}).get_summary(TODAY, days=0)
