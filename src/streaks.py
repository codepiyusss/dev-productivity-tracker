from collections import Counter
from datetime import date, datetime
from typing import Dict, List


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
