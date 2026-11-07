from datetime import date, timedelta

from src.database import Database
from src.main import describe_streak
from src.models.task import Task
from src.tasks import TaskManager


def test_first_completion_starts_a_one_day_streak():
    manager = TaskManager(Database(":memory:"))
    task = manager.create_task("Ship it")
    manager.complete_task(task.task_id)

    assert describe_streak(manager) == "Streak: 1 day. Keep it going tomorrow!"


def test_multi_day_streak_message():
    database = Database(":memory:")
    today = date.today()
    for offset in (2, 1):
        stamp = (today - timedelta(days=offset)).isoformat() + "T10:00:00"
        database.add_task(Task("earlier", completed=True, completed_at=stamp))

    manager = TaskManager(database)
    task = manager.create_task("Today")
    manager.complete_task(task.task_id)

    assert describe_streak(manager) == "Streak: 3 days. Keep it going!"
