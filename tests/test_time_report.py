from src.database import Database
from src.reports import ProductivityReports
from src.tasks import TaskManager
from src.timetracking import TimeTracker


def test_report_has_no_time_section_without_entries():
    database = Database(":memory:")
    TaskManager(database).create_task("Still pending")

    report = ProductivityReports(database).generate_text_report()

    assert "TIME TRACKING" not in report


def test_report_includes_time_section():
    database = Database(":memory:")
    task = TaskManager(database).create_task("Write docs", category="work")
    TimeTracker(database).log_manual(task.task_id, 5400)

    report = ProductivityReports(database).generate_text_report()

    assert "TIME TRACKING" in report
    assert "Time tracked in the last 7 day(s): 1h 30m (1 entry)" in report
    assert "  work: 1h 30m" in report
    assert "  [1] Write docs: 1h 30m" in report


def test_time_section_sits_before_insights_and_keeps_other_sections():
    database = Database(":memory:")
    task = TaskManager(database).create_task("Write docs")
    TimeTracker(database).log_manual(task.task_id, 600)

    report = ProductivityReports(database).generate_text_report()

    assert report.index("TIME TRACKING") < report.index("INSIGHTS")
    assert "PRODUCTIVITY REPORT" in report
    assert "COMPLETION BY PRIORITY" in report
