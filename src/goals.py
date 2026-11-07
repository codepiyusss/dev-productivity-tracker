from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

PERIODS = ("daily", "weekly")
MAX_TARGET = 1000


class GoalTracker:
    """Set completion targets and measure progress against them."""

    def __init__(self, database):
        self.database = database

    @staticmethod
    def _validate_period(period: str) -> str:
        period = str(period).strip().casefold()

        if period not in PERIODS:
            raise ValueError(
                f"Period must be one of: {', '.join(PERIODS)}."
            )

        return period

    def set_goal(self, period: str, target: int) -> None:
        period = self._validate_period(period)

        if isinstance(target, bool) or not isinstance(target, int):
            raise ValueError("Target must be a whole number.")

        if not 1 <= target <= MAX_TARGET:
            raise ValueError(f"Target must be between 1 and {MAX_TARGET}.")

        self.database.set_goal(period, target)

    def clear_goal(self, period: str) -> bool:
        return self.database.clear_goal(self._validate_period(period))

    @staticmethod
    def period_range(period: str, today: Optional[date] = None):
        """First and last day (inclusive) of the period containing today.

        Weekly periods run Monday to Sunday.
        """
        today = today or date.today()

        if period == "weekly":
            start = today - timedelta(days=today.weekday())
            return start, start + timedelta(days=6)

        return today, today

    def count_completed(self, start: date, end: date) -> int:
        """Tasks completed between two dates, inclusive.

        Tasks completed before completion times were tracked have no
        timestamp, so they cannot be placed in a period and are skipped.
        """
        total = 0

        for task in self.database.get_all_tasks(completed=True):
            if not task.completed_at:
                continue

            try:
                done_on = datetime.fromisoformat(task.completed_at).date()
            except ValueError:
                continue

            if start <= done_on <= end:
                total += 1

        return total

    def get_progress(
        self, period: str, today: Optional[date] = None
    ) -> Optional[Dict]:
        """Progress toward one goal, or None if no goal is set."""
        period = self._validate_period(period)
        target = self.database.get_goal(period)

        if target is None:
            return None

        start, end = self.period_range(period, today)
        completed = self.count_completed(start, end)

        return {
            "period": period,
            "target": target,
            "completed": completed,
            "remaining": max(target - completed, 0),
            "percent": min(round(completed / target * 100, 1), 100),
            "met": completed >= target,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }

    def get_all_progress(self, today: Optional[date] = None) -> List[Dict]:
        progress = (self.get_progress(period, today) for period in PERIODS)
        return [item for item in progress if item is not None]
