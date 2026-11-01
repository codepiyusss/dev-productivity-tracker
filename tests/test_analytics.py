from datetime import date, timedelta

from src.analytics import ProductivityAnalytics
from src.database import Database
from src.tasks import TaskManager


def create_manager():
    database = Database(":memory:")
    return TaskManager(database), database


def test_empty_overview():
    _, database = create_manager()
    analytics = ProductivityAnalytics(database)

    assert analytics.get_overview() == {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "completion_rate": 0
    }


def test_overview_and_breakdowns():
    manager, database = create_manager()
    manager.create_task("Study Python", priority="high", category="study")
    manager.create_task("Read documentation", priority="low", category="learning")

    analytics = ProductivityAnalytics(database)

    assert analytics.get_overview()["total"] == 2
    assert analytics.get_priority_breakdown() == {"high": 1, "low": 1}
    assert analytics.get_category_breakdown() == {
        "study": 1, "learning": 1
    }


def test_completion_rate():
    manager, database = create_manager()
    task = manager.create_task("Complete project")
    manager.complete_task(task.task_id)

    analytics = ProductivityAnalytics(database)

    assert analytics.get_overview()["completion_rate"] == 100


def test_weekly_summary_has_seven_days():
    _, database = create_manager()
    analytics = ProductivityAnalytics(database)

    assert len(analytics.get_weekly_summary()) == 7
