from datetime import date, datetime, time, timedelta
from typing import Dict, Iterable, List, Optional

from src.analytics import ProductivityAnalytics
from src.goals import GoalTracker
from src.streaks import StreakTracker
from src.timetracking import TimeTracker


def _date_of(value: Optional[str]) -> Optional[date]:
    try:
        return datetime.fromisoformat(value).date() if value else None
    except ValueError:
        return None


def build_review(
    database,
    days: int = 7,
    today: Optional[date] = None,
    now: Optional[datetime] = None,
    journal_entries: Optional[Iterable[Dict]] = None
) -> Dict:
    """A look back at the last `days` days, ending today.

    Counts what was completed and created, which days were active, and the
    busiest day. Completion dates come from `completed_at`, so tasks finished
    before completion times were tracked cannot be placed on a day and are
    not counted here.
    """
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("Days must be a whole number of at least 1.")

    today = today or date.today()
    first_day = today - timedelta(days=days - 1)
    all_tasks = database.get_all_tasks()

    completed: List = []
    created = 0

    for task in all_tasks:
        done_on = _date_of(task.completed_at) if task.completed else None
        if done_on and first_day <= done_on <= today:
            completed.append((task.completed_at, task.task_id, task))

        made_on = _date_of(task.created_at)
        if made_on and first_day <= made_on <= today:
            created += 1

    completed_tasks = [task for _, _, task in sorted(completed)]
    counts = StreakTracker(database).get_daily_counts()
    per_day = [
        {"date": (first_day + timedelta(days=i)).isoformat(),
         "completed": counts.get(first_day + timedelta(days=i), 0)}
        for i in range(days)
    ]
    busiest = max(per_day, key=lambda day: (day["completed"], day["date"]))

    if now is None:
        now = (
            datetime.now() if today == date.today()
            else datetime.combine(today, time(23, 59, 59))
        )

    time_summary = TimeTracker(database).get_summary(days, now)
    daily_target = database.get_goal("daily")
    journal_days = {
        entry["entry_date"] for entry in (journal_entries or [])
        if first_day.isoformat() <= entry["entry_date"] <= today.isoformat()
    }

    return {
        "days": days,
        "first_day": first_day,
        "last_day": today,
        "completed_tasks": completed_tasks,
        "completed_count": len(completed_tasks),
        "created_count": created,
        "per_day": per_day,
        "active_days": sum(1 for day in per_day if day["completed"]),
        "busiest_day": busiest if busiest["completed"] else None,
        "time": {
            "total_seconds": time_summary["total_seconds"],
            "by_category": time_summary["by_category"][:3],
            "by_task": time_summary["by_task"][:3],
        },
        "daily_goal": (
            {"target": daily_target,
             "days_met": sum(1 for day in per_day if day["completed"] >= daily_target)}
            if daily_target else None
        ),
        "weekly_goal": GoalTracker(database).get_progress("weekly", today),
        "journal_entries": len(journal_days),
        "overdue_count": len(ProductivityAnalytics(database).get_overdue_tasks(today)),
        "streak": StreakTracker(database).current_streak(today)["length"],
    }
