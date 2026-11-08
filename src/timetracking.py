import sqlite3
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

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

    def log_manual(
        self,
        task_id: int,
        seconds: int,
        day: Optional[date] = None,
        now: Optional[datetime] = None
    ) -> Dict:
        """Record time that was not tracked with a timer.

        Without `day` (or for today) the time ends now. For an earlier day
        the entry is placed at 09:00 on that day. Future days are rejected.
        """
        now = now or datetime.now()

        if self.database.get_task(task_id) is None:
            raise ValueError(f"Task {task_id} not found.")

        if seconds <= 0:
            raise ValueError("Duration must be greater than zero.")

        if day is not None and day > now.date():
            raise ValueError("Cannot log time on a future date.")

        if day is None or day == now.date():
            ended = now
            started = ended - timedelta(seconds=seconds)
        else:
            started = datetime.combine(day, time(9, 0))
            ended = started + timedelta(seconds=seconds)

        return self.database.add_time_entry(task_id, _stamp(started), _stamp(ended))

    def list_entries(
        self,
        task_id: Optional[int] = None,
        days: int = 7,
        now: Optional[datetime] = None
    ) -> List[Dict]:
        """Entries from the last `days` days, oldest first, with titles."""
        if days < 1:
            raise ValueError("days must be at least 1.")

        now = now or datetime.now()
        first_day = now.date() - timedelta(days=days - 1)
        entries = self.database.get_time_entries(
            task_id=task_id,
            since=_stamp(datetime.combine(first_day, time.min))
        )

        result = []
        for entry in entries:
            task = self.database.get_task(entry["task_id"])
            result.append({
                **entry,
                "title": task.title if task else "(deleted task)",
                "seconds": entry_seconds(entry, now),
            })

        return result

    def total_seconds(self, task_id: int, now: Optional[datetime] = None) -> int:
        """All time recorded on a task, including a timer still running."""
        now = now or datetime.now()

        return sum(
            entry_seconds(entry, now)
            for entry in self.database.get_time_entries(task_id=task_id)
        )

    def get_summary(self, days: int = 7, now: Optional[datetime] = None) -> Dict:
        """Time spent over the last `days` days, ending today.

        Each entry counts on the day it started. A running timer is
        included up to `now`.
        """
        if days < 1:
            raise ValueError("days must be at least 1.")

        now = now or datetime.now()
        today = now.date()
        first_day = today - timedelta(days=days - 1)
        entries = self.database.get_time_entries(
            since=_stamp(datetime.combine(first_day, time.min)),
            until=_stamp(datetime.combine(today + timedelta(days=1), time.min)),
        )

        per_day = {first_day + timedelta(days=i): 0 for i in range(days)}
        per_task: Dict[int, int] = {}

        for entry in entries:
            seconds = entry_seconds(entry, now)
            per_day[_parse(entry["started_at"]).date()] += seconds
            per_task[entry["task_id"]] = per_task.get(entry["task_id"], 0) + seconds

        by_task = []
        per_category: Dict[str, int] = {}

        for task_id, seconds in per_task.items():
            task = self.database.get_task(task_id)
            by_task.append({
                "task_id": task_id,
                "title": task.title if task else "(deleted task)",
                "seconds": seconds,
            })
            category = task.category if task else "unknown"
            per_category[category] = per_category.get(category, 0) + seconds

        by_task.sort(key=lambda item: (-item["seconds"], item["task_id"]))

        return {
            "days": days,
            "total_seconds": sum(per_day.values()),
            "entry_count": len(entries),
            "by_day": [
                {"date": day.isoformat(), "seconds": seconds}
                for day, seconds in per_day.items()
            ],
            "by_task": by_task,
            "by_category": [
                {"category": name, "seconds": seconds}
                for name, seconds in sorted(
                    per_category.items(), key=lambda pair: (-pair[1], pair[0])
                )
            ],
        }

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
