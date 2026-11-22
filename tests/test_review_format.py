from datetime import date

from src.models.task import Task
from src.review import format_review


def review(**overrides):
    base = {
        "days": 7, "first_day": date(2026, 11, 4), "last_day": date(2026, 11, 10),
        "completed_tasks": [], "completed_count": 0, "created_count": 0,
        "per_day": [{"date": f"2026-11-{d:02d}", "completed": 0} for d in range(4, 11)],
        "active_days": 0, "busiest_day": None,
        "time": {"total_seconds": 0, "by_category": [], "by_task": []},
        "daily_goal": None, "weekly_goal": None, "journal_entries": 0,
        "overdue_count": 0, "streak": 0,
    }
    base.update(overrides)
    return base


def test_quiet_week():
    assert format_review(review()).splitlines() == [
        "Review: 2026-11-04 to 2026-11-10 (7 days)",
        "",
        "Completed: 0 tasks (created: 0)",
        "Active days: 0 of 7",
        "Activity: [-------] (oldest to today)",
        "Time tracked: none",
        "Journal: written on 0 days",
    ]


def test_busy_week_with_everything():
    finished = [
        Task("Ship it", task_id=3, completed=True, completed_at="2026-11-08T09:00:00"),
        Task("Test it", task_id=5, completed=True, completed_at="2026-11-10T09:00:00"),
    ]
    per_day = [{"date": f"2026-11-{d:02d}", "completed": 0} for d in range(4, 11)]
    per_day[4]["completed"] = 1
    per_day[6]["completed"] = 1

    text = format_review(review(
        completed_tasks=finished, completed_count=2, created_count=4,
        per_day=per_day, active_days=2, busiest_day={"date": "2026-11-10", "completed": 1},
        time={"total_seconds": 7200,
              "by_category": [{"category": "work", "seconds": 5400},
                              {"category": "home", "seconds": 1800}], "by_task": []},
        daily_goal={"target": 1, "days_met": 2},
        weekly_goal={"period": "weekly", "target": 5, "completed": 2, "remaining": 3,
                     "percent": 40.0, "met": False},
        journal_entries=1, overdue_count=1, streak=2,
    ))

    assert text.splitlines() == [
        "Review: 2026-11-04 to 2026-11-10 (7 days)",
        "",
        "Completed: 2 tasks (created: 4)",
        "Active days: 2 of 7",
        "Busiest day: 2026-11-10 (1 task)",
        "Activity: [----#-#] (oldest to today)",
        "Time tracked: 2h (work 1h 30m, home 30m)",
        "Daily goal met on 2 of 7 days (target: 1 per day)",
        "Weekly goal: [####------] 2/5 (40.0%) - 3 to go",
        "Journal: written on 1 day",
        "Streak: 2 days",
        "Overdue now: 1 task",
        "",
        "Finished:",
        "  [3] Ship it (2026-11-08)",
        "  [5] Test it (2026-11-10)",
    ]


def test_finished_list_is_capped_with_a_remainder():
    finished = [
        Task(f"T{n}", task_id=n, completed=True, completed_at="2026-11-10T09:00:00")
        for n in range(1, 14)
    ]

    text = format_review(review(completed_tasks=finished, completed_count=13))

    assert "  [10] T10 (2026-11-10)" in text and "[11] T11" not in text
    assert "  ...and 3 more." in text


def test_singular_day_window():
    text = format_review(review(days=1, first_day=date(2026, 11, 10),
                                per_day=[{"date": "2026-11-10", "completed": 0}]))

    assert "(1 day)" in text and "Active days: 0 of 1" in text
