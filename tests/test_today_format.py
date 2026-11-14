from datetime import date

from src.models.task import Task
from src.today import format_today

TODAY = date(2026, 11, 10)   # a Tuesday


def summary(**overrides):
    base = {
        "date": TODAY, "overdue": [], "due_today": [], "upcoming": [],
        "upcoming_days": 3, "pending_count": 0, "ready_count": 0,
        "blocked_count": 0, "timer": None, "goals": [],
        "streak": {"length": 0, "active_today": False, "last_active": None},
        "done_today": 0,
    }
    base.update(overrides)
    return base


def task(number, title, **kwargs):
    return Task(title, task_id=number, **kwargs)


def test_empty_day():
    assert format_today(summary()).splitlines() == [
        "Today: 2026-11-10 (Tuesday)",
        "",
        "Nothing is due in the next 3 days.",
        "",
        "Completed today: 0",
    ]


def test_all_sections_in_order():
    text = format_today(summary(
        overdue=[task(1, "Pay rent", due_date="2026-11-01")],
        due_today=[task(2, "Standup", priority="high")],
        upcoming=[task(3, "Report", due_date="2026-11-12")],
        pending_count=5, ready_count=4, blocked_count=1,
        timer={"task_id": 2, "title": "Standup", "seconds": 1500},
        goals=[{"period": "daily", "target": 3, "completed": 1,
                "remaining": 2, "percent": 33.3, "met": False}],
        streak={"length": 2, "active_today": True, "last_active": TODAY},
        done_today=1,
    ))

    assert text.splitlines() == [
        "Today: 2026-11-10 (Tuesday)",
        "",
        "Timer running on task 2: Standup (25m)",
        "",
        "Overdue (1):",
        "  [1] Pay rent - due 2026-11-01",
        "",
        "Due today (1):",
        "  [2] Standup (high priority)",
        "",
        "Coming up (next 3 days) (1):",
        "  [3] Report - due 2026-11-12",
        "",
        "Pending: 5 (4 ready to start, 1 blocked)",
        "",
        "Daily goal: [###-------] 1/3 (33.3%) - 2 to go",
        "",
        "Completed today: 1",
        "Streak: 2 days",
    ]


def test_sections_without_tasks_are_left_out():
    text = format_today(summary(due_today=[task(2, "Standup")], pending_count=1, ready_count=1))

    assert "Overdue" not in text and "Coming up" not in text
    assert "Nothing is due" not in text
    assert "Pending: 1 (1 ready to start)" in text


def test_singular_streak_wording():
    text = format_today(summary(streak={"length": 1, "active_today": True, "last_active": TODAY}))

    assert "Streak: 1 day" in text and "1 days" not in text


def test_no_streak_line_without_a_streak():
    assert "Streak" not in format_today(summary())


def test_no_pending_line_when_nothing_is_pending():
    assert "Pending:" not in format_today(summary())
