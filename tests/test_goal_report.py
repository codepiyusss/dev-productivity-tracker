from src.database import Database
from src.goals import GoalTracker
from src.reports import ProductivityReports
from src.tasks import TaskManager


def test_report_has_no_goals_section_without_goals():
    report = ProductivityReports(Database(":memory:")).generate_text_report()

    assert "GOALS" not in report


def test_report_shows_goal_progress():
    database = Database(":memory:")
    manager = TaskManager(database)
    task = manager.create_task("Finish feature")
    manager.complete_task(task.task_id)
    tracker = GoalTracker(database)
    tracker.set_goal("daily", 2)
    tracker.set_goal("weekly", 5)

    report = ProductivityReports(database).generate_text_report()

    assert "GOALS" in report
    assert "Daily goal: [#####-----] 1/2 (50.0%) - 1 to go" in report
    assert "Weekly goal:" in report
    # Existing sections are still present.
    assert "PRODUCTIVITY REPORT" in report
    assert "INSIGHTS" in report
