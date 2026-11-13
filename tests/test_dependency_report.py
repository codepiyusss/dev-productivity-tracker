from src.database import Database
from src.dependencies import DependencyManager
from src.reports import ProductivityReports
from src.tasks import TaskManager


def build():
    database = Database(":memory:")
    manager = TaskManager(database)
    for title in ("Design", "Build", "Ship"):
        manager.create_task(title)
    return database, manager, DependencyManager(database)


def test_no_blocked_section_without_dependencies():
    database, _, _ = build()

    assert "BLOCKED TASKS" not in ProductivityReports(database).generate_text_report()


def test_report_lists_blocked_tasks_and_what_they_wait_on():
    database, _, dependencies = build()
    dependencies.add(2, 1)
    dependencies.add(3, 1)
    dependencies.add(3, 2)

    report = ProductivityReports(database).generate_text_report()

    assert "BLOCKED TASKS" in report
    assert "[2] Build (waiting on #1)" in report
    assert "[3] Ship (waiting on #1, #2)" in report


def test_finished_blockers_drop_out_of_the_report():
    database, manager, dependencies = build()
    dependencies.add(2, 1)
    dependencies.add(3, 2)
    manager.complete_task(1)

    report = ProductivityReports(database).generate_text_report()

    assert "[2] Build (waiting" not in report   # its only blocker is done
    assert "[3] Ship (waiting on #2)" in report


def test_section_disappears_when_nothing_is_blocked():
    database, manager, dependencies = build()
    dependencies.add(2, 1)
    manager.complete_task(1)

    assert "BLOCKED TASKS" not in ProductivityReports(database).generate_text_report()


def test_original_sections_are_still_present():
    database, _, dependencies = build()
    dependencies.add(2, 1)

    report = ProductivityReports(database).generate_text_report()

    assert "PRODUCTIVITY REPORT" in report
    assert "INSIGHTS" in report
