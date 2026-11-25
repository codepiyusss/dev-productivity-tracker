from datetime import date

import pytest

from src.models.task import Task
from src.task_filters import filter_by_due

TODAY = date(2026, 11, 10)


@pytest.fixture
def tasks():
    return [
        Task("Late", due_date="2026-11-01"),
        Task("Yesterday", due_date="2026-11-09"),
        Task("Today", due_date="2026-11-10"),
        Task("Tomorrow", due_date="2026-11-11"),
        Task("In a week", due_date="2026-11-17"),
        Task("In eight days", due_date="2026-11-18"),
        Task("No date"),
        Task("Done and late", due_date="2026-11-01", completed=True),
        Task("Legacy date", due_date="31-12-2026"),
    ]


def titles(selected):
    return [t.title for t in selected]


def test_overdue(tasks):
    assert titles(filter_by_due(tasks, "overdue", today=TODAY)) == ["Late", "Yesterday"]


def test_due_today(tasks):
    assert titles(filter_by_due(tasks, "today", today=TODAY)) == ["Today"]


def test_within_includes_today_and_the_last_day(tasks):
    assert titles(filter_by_due(tasks, "within", days=7, today=TODAY)) == [
        "Today", "Tomorrow", "In a week",
    ]


def test_within_zero_days_is_just_today(tasks):
    assert titles(filter_by_due(tasks, "within", days=0, today=TODAY)) == ["Today"]


def test_no_due_date(tasks):
    assert titles(filter_by_due(tasks, "none", today=TODAY)) == ["No date"]


def test_completed_tasks_are_never_returned(tasks):
    for mode in ("overdue", "today", "within", "none"):
        assert "Done and late" not in titles(filter_by_due(tasks, mode, days=30, today=TODAY))


def test_unreadable_legacy_dates_are_skipped_not_crashing(tasks):
    for mode in ("overdue", "today", "within"):
        assert "Legacy date" not in titles(filter_by_due(tasks, mode, days=365, today=TODAY))
    assert "Legacy date" not in titles(filter_by_due(tasks, "none", today=TODAY))


def test_original_order_is_preserved(tasks):
    reversed_tasks = list(reversed(tasks))

    assert titles(filter_by_due(reversed_tasks, "overdue", today=TODAY)) == ["Yesterday", "Late"]


def test_empty_input(tasks):
    assert filter_by_due([], "overdue", today=TODAY) == []


def test_invalid_arguments_are_rejected(tasks):
    with pytest.raises(ValueError, match="overdue, today, within, none"):
        filter_by_due(tasks, "soon")
    for days in (None, -1, 2.5, "7", True):
        with pytest.raises(ValueError, match="at least 0"):
            filter_by_due(tasks, "within", days=days)
