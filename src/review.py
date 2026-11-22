from datetime import date, datetime, time, timedelta
from typing import Dict, Iterable, List, Optional

from src.analytics import ProductivityAnalytics
from src.goals import GoalTracker, format_progress
from src.streaks import StreakTracker
from src.timetracking import TimeTracker
from src.utils import format_duration, pluralize


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


MAX_LISTED = 10


def format_review(review: Dict) -> str:
    """Readable text for a review from `build_review`."""
    days = review["days"]
    lines = [
        f"Review: {review['first_day'].isoformat()} to {review['last_day'].isoformat()} "
        f"({pluralize(days, 'day')})",
        "",
        f"Completed: {pluralize(review['completed_count'], 'task')} "
        f"(created: {review['created_count']})",
        f"Active days: {review['active_days']} of {days}",
    ]

    busiest = review["busiest_day"]
    if busiest:
        lines.append(
            f"Busiest day: {busiest['date']} ({pluralize(busiest['completed'], 'task')})"
        )

    strip = "".join("#" if day["completed"] else "-" for day in review["per_day"])
    lines.append(f"Activity: [{strip}] (oldest to today)")

    time_info = review["time"]
    if time_info["total_seconds"]:
        categories = ", ".join(
            f"{item['category']} {format_duration(item['seconds'])}"
            for item in time_info["by_category"]
        )
        lines.append(f"Time tracked: {format_duration(time_info['total_seconds'])} ({categories})")
    else:
        lines.append("Time tracked: none")

    goal = review["daily_goal"]
    if goal:
        lines.append(
            f"Daily goal met on {goal['days_met']} of {days} days (target: {goal['target']} per day)"
        )
    if review["weekly_goal"]:
        lines.append(format_progress(review["weekly_goal"]))

    lines.append(f"Journal: written on {pluralize(review['journal_entries'], 'day')}")
    if review["streak"]:
        lines.append(f"Streak: {pluralize(review['streak'], 'day')}")
    if review["overdue_count"]:
        lines.append(f"Overdue now: {pluralize(review['overdue_count'], 'task')}")

    finished = review["completed_tasks"]
    if finished:
        lines += ["", "Finished:"]
        for task in finished[:MAX_LISTED]:
            lines.append(f"  [{task.task_id}] {task.title} ({task.completed_at[:10]})")
        if len(finished) > MAX_LISTED:
            lines.append(f"  ...and {len(finished) - MAX_LISTED} more.")

    return "\n".join(lines)
