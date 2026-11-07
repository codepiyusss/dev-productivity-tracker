from datetime import date

from src.main import format_task_line, is_overdue
from src.models.task import Task

TODAY = date(2026, 11, 10)


def line(**kwargs):
    return format_task_line(Task("Ship it", task_id=3, **kwargs), TODAY)


def test_line_without_due_date_is_unchanged():
    assert line() == "[3] Ship it | medium | general | Pending"


def test_future_due_date_is_shown():
    assert line(due_date="2026-12-01") == (
        "[3] Ship it | medium | general | Pending | due 2026-12-01"
    )


def test_due_today_is_not_overdue():
    assert "OVERDUE" not in line(due_date="2026-11-10")


def test_past_due_pending_task_is_flagged():
    assert line(due_date="2026-11-01").endswith("| due 2026-11-01 (OVERDUE)")


def test_completed_task_is_never_flagged():
    text = line(due_date="2026-11-01", completed=True)

    assert "due 2026-11-01" in text
    assert "OVERDUE" not in text


def test_tags_come_after_the_due_date():
    text = line(due_date="2026-12-01", tags=["work", "urgent"])

    assert text.endswith("| due 2026-12-01 | #work #urgent")


def test_unreadable_legacy_due_date_does_not_crash():
    assert "OVERDUE" not in line(due_date="31-12-2026")
    assert is_overdue("garbage", TODAY) is False
