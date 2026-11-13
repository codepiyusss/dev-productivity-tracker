from datetime import date

from src.analytics import ProductivityAnalytics
from src.database import Database
from src.dependencies import DependencyManager
from src.tasks import TaskManager

TODAY = date(2026, 11, 12)


def setup(count=3):
    database = Database(":memory:")
    manager = TaskManager(database)
    for number in range(count):
        manager.create_task(f"Task {number + 1}")
    return database, manager, DependencyManager(database)


def blocked_insights(database):
    return [i for i in ProductivityAnalytics(database).get_insights(TODAY) if "blocked" in i]


def test_no_insight_without_dependencies():
    database, _, _ = setup()

    assert blocked_insights(database) == []


def test_blocked_tasks_are_counted():
    database, _, dependencies = setup()
    dependencies.add(2, 1)
    dependencies.add(3, 1)

    assert blocked_insights(database) == ["2 task(s) are blocked by unfinished tasks."]


def test_insight_disappears_once_blockers_are_done():
    database, manager, dependencies = setup()
    dependencies.add(2, 1)
    manager.complete_task(1)

    assert blocked_insights(database) == []


def test_completed_dependents_are_not_counted():
    database, manager, dependencies = setup()
    dependencies.add(2, 1)
    manager.complete_task(2)

    assert blocked_insights(database) == []
