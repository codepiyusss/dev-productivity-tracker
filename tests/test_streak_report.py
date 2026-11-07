from src.database import Database
from src.reports import ProductivityReports
from src.tasks import TaskManager


def test_report_has_no_streak_section_without_completions():
    database = Database(":memory:")
    TaskManager(database).create_task("Still pending")

    report = ProductivityReports(database).generate_text_report()

    assert "STREAKS" not in report


def test_report_includes_streak_section_after_a_completion():
    database = Database(":memory:")
    manager = TaskManager(database)
    task = manager.create_task("Ship it")
    manager.complete_task(task.task_id)

    report = ProductivityReports(database).generate_text_report()

    assert "STREAKS" in report
    assert "Current streak: 1 day (completed a task today)" in report
    assert "Active days: 1" in report
    # Earlier sections are untouched.
    assert "INSIGHTS" in report
    assert "PRODUCTIVITY REPORT" in report
