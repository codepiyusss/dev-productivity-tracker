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
