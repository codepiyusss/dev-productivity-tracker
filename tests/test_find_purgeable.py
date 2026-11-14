from datetime import date

import pytest

from src.database import Database
from src.housekeeping import find_purgeable
from src.models.task import Task

TODAY = date(2026, 11, 10)


@pytest.fixture
def database():
    db = Database(":memory:")

    def done(title, completed_at):
        db.add_task(Task(title, completed=True, completed_at=completed_at))

    done("Finished 100 days ago", "2026-08-02T09:00:00")
    done("Finished 31 days ago", "2026-10-10T23:59:59")
    done("Finished 30 days ago", "2026-10-11T00:00:01")
    done("Finished 29 days ago", "2026-10-12T09:00:00")
    done("Finished today", "2026-11-10T08:00:00")
    db.add_task(Task("Still pending"))
    db.add_task(Task("Legacy done, no date", completed=True))
    db.add_task(Task("Garbled date", completed=True, completed_at="not-a-date"))
    return db


def titles(tasks):
    return [t.title for t in tasks]


def test_only_tasks_completed_long_enough_ago_are_returned(database):
    result = find_purgeable(database, 30, TODAY)

    assert titles(result) == [
        "Finished 100 days ago", "Finished 31 days ago", "Finished 30 days ago",
    ]


def test_boundary_is_inclusive_of_exactly_n_days(database):
    assert "Finished 30 days ago" in titles(find_purgeable(database, 30, TODAY))
    assert "Finished 29 days ago" not in titles(find_purgeable(database, 30, TODAY))
    assert "Finished 29 days ago" in titles(find_purgeable(database, 29, TODAY))


def test_pending_tasks_are_never_included(database):
    assert "Still pending" not in titles(find_purgeable(database, 1, TODAY))


def test_tasks_without_a_known_date_are_excluded_by_default(database):
    result = titles(find_purgeable(database, 1, TODAY))

    assert "Legacy done, no date" not in result
    assert "Garbled date" not in result


def test_include_undated_adds_them_at_the_end(database):
    result = titles(find_purgeable(database, 30, TODAY, include_undated=True))

    assert result[:3] == [
        "Finished 100 days ago", "Finished 31 days ago", "Finished 30 days ago",
    ]
    assert result[3:] == ["Legacy done, no date", "Garbled date"]


def test_result_is_oldest_first(database):
    result = find_purgeable(database, 1, TODAY)

    assert titles(result) == [
        "Finished 100 days ago", "Finished 31 days ago",
        "Finished 30 days ago", "Finished 29 days ago",
    ]   # "Finished today" is 0 days old, so it is not included


def test_nothing_to_purge(database):
    assert find_purgeable(database, 365, TODAY) == []
    assert find_purgeable(Database(":memory:"), 30, TODAY) == []


@pytest.mark.parametrize("days", [0, -5, 2.5, "30", True])
def test_invalid_days_are_rejected(database, days):
    with pytest.raises(ValueError, match="at least 1"):
        find_purgeable(database, days, TODAY)
