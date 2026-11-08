import sqlite3
from datetime import datetime
from typing import Dict, Optional

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _stamp(moment: datetime) -> str:
    return moment.strftime(TIMESTAMP_FORMAT)


def _parse(value: str) -> datetime:
    return datetime.strptime(value, TIMESTAMP_FORMAT)


class TimeTracker:
    """Track time spent on tasks with a start/stop timer or manual entries."""

    def __init__(self, database):
        self.database = database

    def start(self, task_id: int, now: Optional[datetime] = None) -> Dict:
        """Start a timer on a task. Only one timer can run at a time."""
        if self.database.get_task(task_id) is None:
            raise ValueError(f"Task {task_id} not found.")

        running = self.database.get_running_entry()
        if running is not None:
            raise ValueError(
                f"A timer is already running on task {running['task_id']}. "
                "Stop it first."
            )

        try:
            return self.database.add_time_entry(
                task_id, _stamp(now or datetime.now())
            )
        except sqlite3.IntegrityError:
            # Another process started a timer between the check and insert.
            raise ValueError("A timer is already running. Stop it first.")
