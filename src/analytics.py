from datetime import date, timedelta
from collections import Counter

from src.streaks import StreakTracker


class ProductivityAnalytics:
    def __init__(self, database):
        self.database = database

    def get_overview(self):
        tasks = self.database.get_all_tasks()
        total = len(tasks)
        completed = sum(task.completed for task in tasks)
        pending = total - completed

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_rate": round(
                (completed / total) * 100, 2
            ) if total else 0
        }

    def get_priority_breakdown(self):
        tasks = self.database.get_all_tasks()
        return dict(Counter(task.priority for task in tasks))

    def get_category_breakdown(self):
        tasks = self.database.get_all_tasks()
        return dict(Counter(task.category for task in tasks))

    @staticmethod
    def _parse_date(value):
        """Return a date from 'YYYY-MM-DD...' text, or None if invalid."""
        try:
            return date.fromisoformat(value[:10]) if value else None
        except ValueError:
            return None

    @staticmethod
    def _rate(completed, total):
        return round((completed / total) * 100, 2) if total else 0

    def get_overdue_tasks(self, today=None):
        today = today or date.today()
        overdue = []

        for task in self.database.get_all_tasks(completed=False):
            due = self._parse_date(task.due_date)
            if due and due < today:
                overdue.append(task)

        return overdue

    def get_due_soon_tasks(self, days=7, today=None):
        """Pending tasks due from today up to `days` days ahead."""
        today = today or date.today()
        last_day = today + timedelta(days=days)
        due_soon = []

        for task in self.database.get_all_tasks(completed=False):
            due = self._parse_date(task.due_date)
            if due and today <= due <= last_day:
                due_soon.append((due, task))

        return [task for _, task in sorted(due_soon, key=lambda pair: pair[0])]

    def _completion_by(self, keys_for_task):
        groups = {}

        for task in self.database.get_all_tasks():
            for key in keys_for_task(task):
                entry = groups.setdefault(key, {"total": 0, "completed": 0})
                entry["total"] += 1
                entry["completed"] += int(task.completed)

        return {
            key: {
                **entry,
                "completion_rate": self._rate(entry["completed"], entry["total"])
            }
            for key, entry in sorted(groups.items())
        }

    def get_priority_completion(self):
        return self._completion_by(lambda task: [task.priority])

    def get_category_completion(self):
        return self._completion_by(lambda task: [task.category])

    def get_tag_breakdown(self):
        """Task count and completion rate for each tag."""
        return self._completion_by(lambda task: task.tags)

    def get_pending_age_stats(self, today=None):
        """How long pending tasks have been waiting, in days."""
        today = today or date.today()
        ages = []

        for task in self.database.get_all_tasks(completed=False):
            created = self._parse_date(task.created_at)
            if created:
                ages.append((max((today - created).days, 0), task))

        if not ages:
            return {
                "count": 0, "oldest_days": 0,
                "average_days": 0, "oldest_task": None
            }

        oldest_days, oldest_task = max(ages, key=lambda pair: pair[0])

        return {
            "count": len(ages),
            "oldest_days": oldest_days,
            "average_days": round(sum(a for a, _ in ages) / len(ages), 1),
            "oldest_task": oldest_task.title
        }

    def get_weekday_distribution(self):
        """Tasks created and completed, grouped by weekday of creation."""
        names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]
        result = {name: {"created": 0, "completed": 0} for name in names}

        for task in self.database.get_all_tasks():
            created = self._parse_date(task.created_at)
            if created:
                entry = result[names[created.weekday()]]
                entry["created"] += 1
                entry["completed"] += int(task.completed)

        return result

    def get_recent_trend(self, days=7, today=None):
        """Daily summaries for the last `days` days, oldest first."""
        today = today or date.today()

        return [
            self.get_daily_summary(today - timedelta(days=offset))
            for offset in range(days - 1, -1, -1)
        ]

    def get_insights(self, today=None):
        """Short plain-language observations about the current tasks."""
        overview = self.get_overview()

        if overview["total"] == 0:
            return ["No tasks yet. Add one to start tracking progress."]

        insights = []

        overdue = self.get_overdue_tasks(today)
        if overdue:
            insights.append(f"{len(overdue)} task(s) are overdue.")

        due_soon = self.get_due_soon_tasks(today=today)
        if due_soon:
            insights.append(f"{len(due_soon)} task(s) are due in the next 7 days.")

        age = self.get_pending_age_stats(today)
        if age["oldest_days"] >= 7:
            insights.append(
                f"Oldest pending task has waited {age['oldest_days']} days: "
                f"{age['oldest_task']}."
            )

        categories = {
            name: data for name, data in self.get_category_completion().items()
            if data["total"] >= 2
        }
        if categories:
            best = max(categories, key=lambda n: categories[n]["completion_rate"])
            insights.append(
                f"Best completion rate: {best} "
                f"({categories[best]['completion_rate']}%)."
            )

        weekdays = self.get_weekday_distribution()
        busiest = max(weekdays, key=lambda n: weekdays[n]["created"])
        if weekdays[busiest]["created"] > 0:
            insights.append(f"Most tasks are created on {busiest}.")

        if overview["pending"] == 0:
            insights.append("All tasks are completed. Nice work!")

        return insights

    def get_detailed_stats(self, today=None):
        """Everything above in one JSON-friendly dictionary."""
        return {
            "overview": self.get_overview(),
            "priority_completion": self.get_priority_completion(),
            "category_completion": self.get_category_completion(),
            "tags": self.get_tag_breakdown(),
            "overdue": [t.to_dict() for t in self.get_overdue_tasks(today)],
            "due_soon": [t.to_dict() for t in self.get_due_soon_tasks(today=today)],
            "pending_age": self.get_pending_age_stats(today),
            "weekday_distribution": self.get_weekday_distribution(),
            "insights": self.get_insights(today),
        }

    def get_daily_summary(self, target_date=None):
        target_date = target_date or date.today()
        tasks = self.database.get_all_tasks()
        day_tasks = [
            task for task in tasks
            if task.created_at[:10] == target_date.isoformat()
        ]

        completed = sum(task.completed for task in day_tasks)

        return {
            "date": target_date.isoformat(),
            "created": len(day_tasks),
            "completed": completed,
            "pending": len(day_tasks) - completed
        }

    def get_weekly_summary(self):
        today = date.today()
        start = today - timedelta(days=today.weekday())

        return [
            self.get_daily_summary(start + timedelta(days=offset))
            for offset in range(7)
        ]

    def get_completion_streak(self, today=None):
        """Current streak in days, based on when tasks were completed.

        Previously this used each task's creation date, which was wrong for
        tasks completed on a different day than they were created.
        """
        return StreakTracker(self.database).current_streak(today)["length"]
