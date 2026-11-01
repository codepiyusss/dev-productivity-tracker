from datetime import date, timedelta
from collections import Counter


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

    def get_overdue_tasks(self):
        today = date.today()
        return [
            task for task in self.database.get_all_tasks(completed=False)
            if task.due_date and date.fromisoformat(task.due_date) < today
        ]

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

    def get_completion_streak(self):
        tasks = self.database.get_all_tasks(completed=True)
        completion_dates = {
            task.created_at[:10] for task in tasks if task.created_at
        }

        streak = 0
        current_day = date.today()

        while current_day.isoformat() in completion_dates:
            streak += 1
            current_day -= timedelta(days=1)

        return streak
