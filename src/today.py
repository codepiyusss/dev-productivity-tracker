from datetime import date, datetime, timedelta
from typing import Dict, Optional

from src.dependencies import DependencyManager
from src.goals import GoalTracker, format_progress
from src.streaks import StreakTracker
from src.timetracking import TimeTracker
from src.utils import format_duration

UPCOMING_DAYS = 3


def _due(task) -> Optional[date]:
    try:
        return date.fromisoformat(task.due_date) if task.due_date else None
    except ValueError:
        return None


def build_today_summary(
    database, today: Optional[date] = None, now: Optional[datetime] = None
) -> Dict:
    """Everything worth knowing at the start of the day, in one dictionary.

    Overdue, due today and upcoming only include pending tasks, sorted by
    due date. A task counts as ready when no unfinished task blocks it.
    """
    today = today or date.today()
    pending = database.get_all_tasks(completed=False)
    last_upcoming = today + timedelta(days=UPCOMING_DAYS)
    overdue, due_today, upcoming = [], [], []

    for task in pending:
        due = _due(task)

        if due is None:
            continue
        if due < today:
            overdue.append((due, task))
        elif due == today:
            due_today.append((due, task))
        elif due <= last_upcoming:
            upcoming.append((due, task))

    def ordered(pairs):
        return [task for _, task in sorted(pairs, key=lambda p: (p[0], p[1].task_id))]

    blocked_ids = set(DependencyManager(database).get_blocker_map())
    streaks = StreakTracker(database)
    done_today = streaks.get_daily_counts().get(today, 0)

    return {
        "date": today,
        "overdue": ordered(overdue),
        "due_today": ordered(due_today),
        "upcoming": ordered(upcoming),
        "upcoming_days": UPCOMING_DAYS,
        "pending_count": len(pending),
        "ready_count": sum(1 for t in pending if t.task_id not in blocked_ids),
        "blocked_count": sum(1 for t in pending if t.task_id in blocked_ids),
        "timer": TimeTracker(database).status(now),
        "goals": GoalTracker(database).get_all_progress(today),
        "streak": streaks.current_streak(today),
        "done_today": done_today,
    }


def _task_line(task, show_due: bool) -> str:
    line = f"  [{task.task_id}] {task.title}"

    if task.priority == "high":
        line += " (high priority)"

    if show_due and task.due_date:
        line += f" - due {task.due_date}"

    return line


def format_today(summary: Dict) -> str:
    """Readable text for a summary from `build_today_summary`."""
    day = summary["date"]
    lines = [f"Today: {day.isoformat()} ({day.strftime('%A')})"]

    timer = summary["timer"]
    if timer:
        lines += ["", (
            f"Timer running on task {timer['task_id']}: {timer['title']} "
            f"({format_duration(timer['seconds'])})"
        )]

    sections = (
        ("Overdue", summary["overdue"], True),
        ("Due today", summary["due_today"], False),
        (f"Coming up (next {summary['upcoming_days']} days)", summary["upcoming"], True),
    )
    nothing_due = True

    for title, tasks, show_due in sections:
        if tasks:
            nothing_due = False
            lines += ["", f"{title} ({len(tasks)}):"]
            lines += [_task_line(task, show_due) for task in tasks]

    if nothing_due:
        lines += ["", f"Nothing is due in the next {summary['upcoming_days']} days."]

    pending = summary["pending_count"]
    if pending:
        ready = f"{summary['ready_count']} ready to start"
        blocked = summary["blocked_count"]
        extra = f", {blocked} blocked" if blocked else ""
        lines += ["", f"Pending: {pending} ({ready}{extra})"]

    if summary["goals"]:
        lines.append("")
        lines += [format_progress(goal) for goal in summary["goals"]]

    streak = summary["streak"]["length"]
    done = summary["done_today"]
    lines.append("")
    lines.append(f"Completed today: {done}")
    if streak:
        lines.append(f"Streak: {streak} day{'s' if streak != 1 else ''}")

    return "\n".join(lines)
