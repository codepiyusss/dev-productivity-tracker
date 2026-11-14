from datetime import date, datetime, timedelta
from typing import Dict, Optional

from src.dependencies import DependencyManager
from src.goals import GoalTracker
from src.streaks import StreakTracker
from src.timetracking import TimeTracker

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
