import sqlite3
from datetime import datetime
from typing import Dict, Optional

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
STALE_AFTER_SECONDS = 12 * 3600  # a timer this old was probably forgotten


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

    def status(self, now: Optional[datetime] = None) -> Optional[Dict]:
        """Details of the running timer, or None if nothing is running."""
        running = self.database.get_running_entry()

        if running is None:
            return None

        task = self.database.get_task(running["task_id"])
        seconds = entry_seconds(running, now)

        return {
            **running,
            "title": task.title if task else "(deleted task)",
            "seconds": seconds,
            "stale": seconds >= STALE_AFTER_SECONDS,
        }

    def stop(self, now: Optional[datetime] = None) -> Dict:
        """Stop the running timer and return the finished entry."""
        running = self.database.get_running_entry()

        if running is None:
            raise ValueError("No timer is running.")

        started = _parse(running["started_at"])
        ended = max(now or datetime.now(), started)  # never end before start
        self.database.end_time_entry(running["entry_id"], _stamp(ended))

        return {
            **running,
            "ended_at": _stamp(ended),
            "seconds": entry_seconds({**running, "ended_at": _stamp(ended)}),
        }


def entry_seconds(entry: Dict, now: Optional[datetime] = None) -> int:
    """Length of an entry in seconds. Running entries use `now`."""
    started = _parse(entry["started_at"])

    if entry["ended_at"]:
        ended = _parse(entry["ended_at"])
    else:
        ended = now or datetime.now()

    return max(int((ended - started).total_seconds()), 0)
