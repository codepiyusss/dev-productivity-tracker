from collections import Counter
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional


class StreakTracker:
    """Measure how consistently tasks are completed, day by day."""

    def __init__(self, database):
        self.database = database

    def get_daily_counts(self) -> Dict[date, int]:
        """Number of tasks completed on each day that has any.

        Tasks completed before completion times were tracked, or with an
        unreadable timestamp, cannot be placed on a day and are skipped.
        """
        counts = Counter()

        for task in self.database.get_all_tasks(completed=True):
            if not task.completed_at:
                continue

            try:
                counts[datetime.fromisoformat(task.completed_at).date()] += 1
            except ValueError:
                continue

        return dict(counts)

    def get_completion_dates(self) -> List[date]:
        """Sorted list of days on which at least one task was completed."""
        return sorted(self.get_daily_counts())

    def current_streak(self, today: Optional[date] = None) -> Dict:
        """Consecutive days with a completed task, ending today.

        A streak is still alive if the last completion was yesterday, so
        you have until the end of today to extend it.
        """
        today = today or date.today()
        return self._run_ending_at(set(self.get_completion_dates()), today)

    @staticmethod
    def _run_ending_at(days: set, today: date) -> Dict:
        """Length of the consecutive-day run that ends today or yesterday."""
        if today in days:
            end = today
        elif today - timedelta(days=1) in days:
            end = today - timedelta(days=1)
        else:
            return {
                "length": 0,
                "active_today": False,
                "last_active": max((d for d in days if d <= today), default=None),
            }

        length = 0
        day = end

        while day in days:
            length += 1
            day -= timedelta(days=1)

        return {"length": length, "active_today": end == today, "last_active": end}

    def goal_streak(self, today: Optional[date] = None) -> Optional[Dict]:
        """Streak of days on which the daily goal was met.

        Returns None when no daily goal is set.
        """
        target = self.database.get_goal("daily")

        if target is None:
            return None

        today = today or date.today()
        met_days = {
            day for day, count in self.get_daily_counts().items()
            if count >= target
        }

        return {"target": target, **self._run_ending_at(met_days, today)}

    def longest_streak(self) -> Dict:
        """The longest run of consecutive days with a completed task.

        If several runs tie, the most recent one is returned.
        """
        days = self.get_completion_dates()

        if not days:
            return {"length": 0, "start": None, "end": None}

        best = (0, None, None)
        run_start = previous = days[0]
        length = 1

        for day in days[1:] + [None]:
            if day is not None and day - previous == timedelta(days=1):
                length += 1
            else:
                if length >= best[0]:
                    best = (length, run_start, previous)
                run_start, length = day, 1
            previous = day

        return {"length": best[0], "start": best[1], "end": best[2]}

    def get_summary(self, today: Optional[date] = None, days: int = 14) -> Dict:
        """Everything about streaks in one JSON-friendly dictionary.

        `recent` lists the last `days` days, oldest first, ending today.
        """
        if days < 1:
            raise ValueError("days must be at least 1.")

        today = today or date.today()
        counts = self.get_daily_counts()
        current = self.current_streak(today)
        longest = self.longest_streak()
        goal = self.goal_streak(today)

        return {
            "current": current["length"],
            "active_today": current["active_today"],
            "last_active": _iso(current["last_active"]),
            "at_risk": current["length"] > 0 and not current["active_today"],
            "longest": longest["length"],
            "longest_start": _iso(longest["start"]),
            "longest_end": _iso(longest["end"]),
            "goal_streak": goal["length"] if goal else None,
            "daily_target": goal["target"] if goal else None,
            "total_active_days": len(counts),
            "recent": [
                {
                    "date": (today - timedelta(days=offset)).isoformat(),
                    "completed": counts.get(today - timedelta(days=offset), 0),
                }
                for offset in range(days - 1, -1, -1)
            ],
        }


def _iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def _days(count: int) -> str:
    return f"{count} day" if count == 1 else f"{count} days"


def format_streak_summary(summary: Dict) -> str:
    """Readable multi-line text for a summary from `get_summary`."""
    lines = []

    if summary["current"]:
        note = (
            "completed a task today" if summary["active_today"]
            else "complete a task today to keep it going"
        )
        lines.append(f"Current streak: {_days(summary['current'])} ({note})")
    else:
        lines.append("Current streak: 0 days (complete a task to start one)")

    if summary["longest"]:
        lines.append(
            f"Longest streak: {_days(summary['longest'])} "
            f"({summary['longest_start']} to {summary['longest_end']})"
        )
    else:
        lines.append("Longest streak: 0 days")

    if summary["goal_streak"] is not None:
        lines.append(
            f"Goal streak: {_days(summary['goal_streak'])} "
            f"(daily target: {summary['daily_target']})"
        )

    lines.append(f"Active days: {summary['total_active_days']}")

    strip = "".join("#" if day["completed"] else "-" for day in summary["recent"])
    lines.append(f"Last {len(summary['recent'])} days: [{strip}] (oldest to today)")

    return "\n".join(lines)
