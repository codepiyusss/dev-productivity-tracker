from datetime import date

import pytest

from src.database import Database
from src.models.task import Task
from src.review import build_review

TODAY = date(2026, 11, 10)


@pytest.fixture
def database():
    db = Database(":memory:")

    def add(title, created, completed_at=None):
        db.add_task(Task(
            title, created_at=f"{created}T09:00:00",
            completed=bool(completed_at), completed_at=completed_at,
        ))

    add("Done today", "2026-11-08", "2026-11-10T10:00:00")
    add("Done today too", "2026-11-10", "2026-11-10T15:00:00")
    add("Done on the 8th", "2026-11-01", "2026-11-08T09:00:00")
    add("Done too long ago", "2026-10-01", "2026-10-05T09:00:00")
    add("Still pending", "2026-11-09")
    add("Created too long ago", "2026-09-01")
    db.add_task(Task("Legacy done", completed=True, created_at="2026-11-09T09:00:00"))
    return db


def test_counts_for_the_period(database):
    review = build_review(database, 7, TODAY)

    assert review["completed_count"] == 3
    # Created inside the window: "Done today", "Done today too", "Still pending", "Legacy done".
    assert review["created_count"] == 4
    assert (review["first_day"], review["last_day"]) == (date(2026, 11, 4), TODAY)


def test_completed_tasks_are_listed_oldest_first_and_exclude_old_and_undated(database):
    review = build_review(database, 7, TODAY)

    assert [t.title for t in review["completed_tasks"]] == [
        "Done on the 8th", "Done today", "Done today too",
    ]


def test_per_day_breakdown_covers_every_day(database):
    review = build_review(database, 7, TODAY)

    assert [d["date"] for d in review["per_day"]][0] == "2026-11-04"
    assert len(review["per_day"]) == 7
    counts = {d["date"]: d["completed"] for d in review["per_day"]}
    assert counts["2026-11-08"] == 1 and counts["2026-11-10"] == 2
    assert counts["2026-11-09"] == 0


def test_active_days_and_busiest_day(database):
    review = build_review(database, 7, TODAY)

    assert review["active_days"] == 2
    assert review["busiest_day"] == {"date": "2026-11-10", "completed": 2}


def test_busiest_day_tie_prefers_the_most_recent():
    db = Database(":memory:")
    db.add_task(Task("A", completed=True, completed_at="2026-11-08T09:00:00"))
    db.add_task(Task("B", completed=True, completed_at="2026-11-09T09:00:00"))

    assert build_review(db, 7, TODAY)["busiest_day"]["date"] == "2026-11-09"


def test_empty_database():
    review = build_review(Database(":memory:"), 3, TODAY)

    assert review["completed_count"] == 0 and review["created_count"] == 0
    assert review["active_days"] == 0 and review["busiest_day"] is None
    assert len(review["per_day"]) == 3


def test_one_day_window_only_covers_today(database):
    review = build_review(database, 1, TODAY)

    assert review["completed_count"] == 2
    assert [d["date"] for d in review["per_day"]] == ["2026-11-10"]


@pytest.mark.parametrize("days", [0, -1, 2.5, "7", True])
def test_invalid_days_are_rejected(database, days):
    with pytest.raises(ValueError, match="at least 1"):
        build_review(database, days, TODAY)
