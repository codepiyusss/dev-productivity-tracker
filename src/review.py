from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from src.streaks import StreakTracker


def _date_of(value: Optional[str]) -> Optional[date]:
    try:
        return datetime.fromisoformat(value).date() if value else None
    except ValueError:
        return None


def build_review(
    database,
    days: int = 7,
    today: Optional[date] = None
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
    }
