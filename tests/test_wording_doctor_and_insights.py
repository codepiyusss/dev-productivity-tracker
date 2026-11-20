from datetime import date, datetime

from src.analytics import ProductivityAnalytics
from src.database import Database
from src.dependencies import DependencyManager
from src.doctor import CheckResult, check_data, format_doctor_report
from src.models.task import Task
from src.tasks import TaskManager

TODAY = date(2026, 11, 12)
NOW = datetime(2026, 11, 10, 18, 0, 0)


def insights(database):
    return ProductivityAnalytics(database).get_insights(TODAY)


def test_overdue_and_due_soon_singular_and_plural():
    database = Database(":memory:")
    manager = TaskManager(database)
    manager.create_task("A", due_date="2026-11-01")
    assert "1 task is overdue." in insights(database)

    manager.create_task("B", due_date="2026-11-02")
    assert "2 tasks are overdue." in insights(database)

    manager.create_task("C", due_date="2026-11-14")
    assert "1 task is due in the next 7 days." in insights(database)


def test_blocked_insight_singular():
    database = Database(":memory:")
    manager = TaskManager(database)
    manager.create_task("A")
    manager.create_task("B")
    DependencyManager(database).add(2, 1)

    assert "1 task is blocked by unfinished tasks." in insights(database)


def test_doctor_plural_messages(tmp_path):
    path = str(tmp_path / "t.db")
    database = Database(path)
    database.add_task(Task("Bad 1", due_date="31-12-2026"))
    database.add_task(Task("Bad 2", due_date="1/2/2026"))
    database.add_task(Task("Repeat 1", recurrence="daily"))
    database.add_task(Task("Repeat 2", recurrence="weekly"))
    database.add_task(Task("Old 1", completed=True))
    database.add_task(Task("Old 2", completed=True))

    results = {r.name: r for r in check_data(path, NOW)}

    assert "2 tasks have unreadable due dates (IDs: 1, 2)" in results["Due dates"].detail
    assert "Fix them with" in results["Due dates"].detail
    assert "2 repeating tasks have no due date, so they cannot repeat." in results["Repeating tasks"].detail
    assert "2 completed tasks have no completion time" in results["Completion times"].detail
    assert "They do not count toward goals or streaks." in results["Completion times"].detail


def test_doctor_summary_plurals():
    results = [CheckResult("a", "ok", ""), CheckResult("b", "ok", ""), CheckResult("c", "warn", ""),
               CheckResult("d", "warn", ""), CheckResult("e", "fail", ""), CheckResult("f", "fail", "")]

    assert format_doctor_report(results).endswith(
        "2 problems found, 2 warnings, 2 checks passed."
    )
