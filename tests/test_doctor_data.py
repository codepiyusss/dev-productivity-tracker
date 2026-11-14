import sqlite3
from datetime import datetime

import pytest

from src.database import Database
from src.doctor import FAIL, INFO, OK, WARN, check_data
from src.models.task import Task
from src.tasks import TaskManager
from src.timetracking import TimeTracker

NOW = datetime(2026, 11, 10, 18, 0, 0)


@pytest.fixture
def path(tmp_path):
    p = str(tmp_path / "t.db")
    TaskManager(Database(p)).create_task("Healthy", due_date="2026-12-01")
    return p


def by_name(results):
    return {r.name: r for r in results}


def test_clean_database_has_no_warnings(path):
    results = by_name(check_data(path, NOW))

    assert results["Due dates"].status == OK
    assert results["Repeating tasks"].status == OK
    assert results["Timer"].status == OK and "No timer" in results["Timer"].detail
    assert "Completion times" not in results


def test_unreadable_due_dates_are_reported_with_ids(path):
    Database(path).add_task(Task("Legacy", due_date="31-12-2026"))

    result = by_name(check_data(path, NOW))["Due dates"]

    assert result.status == WARN
    assert "1 task(s)" in result.detail and "IDs: 2" in result.detail
    assert "edit ID --due-date" in result.detail


def test_repeating_task_without_due_date_is_reported(path):
    Database(path).add_task(Task("Broken repeat", recurrence="daily"))

    result = by_name(check_data(path, NOW))["Repeating tasks"]

    assert result.status == WARN and "1 repeating task(s)" in result.detail


def test_stale_timer_is_a_warning(path):
    TimeTracker(Database(path)).start(1, datetime(2026, 11, 9, 8, 0, 0))

    result = by_name(check_data(path, NOW))["Timer"]

    assert result.status == WARN and "34 hours" in result.detail


def test_recent_timer_is_fine(path):
    TimeTracker(Database(path)).start(1, datetime(2026, 11, 10, 17, 0, 0))

    result = by_name(check_data(path, NOW))["Timer"]

    assert result.status == OK and "running normally" in result.detail


def test_legacy_completions_are_informational(path):
    Database(path).add_task(Task("Old done", completed=True))

    result = by_name(check_data(path, NOW))["Completion times"]

    assert result.status == INFO and "1 completed task(s)" in result.detail


def test_old_database_without_newer_tables_is_handled(tmp_path):
    p = str(tmp_path / "old.db")
    connection = sqlite3.connect(p)
    with connection:
        connection.execute(
            "CREATE TABLE tasks (task_id INTEGER PRIMARY KEY, title TEXT, due_date TEXT, "
            "completed INTEGER DEFAULT 0)"
        )
        connection.execute("INSERT INTO tasks (title, due_date) VALUES ('Old', '2026-12-01')")
    connection.close()

    results = by_name(check_data(p, NOW))

    assert results["Due dates"].status == OK
    assert results["Timer"].status == OK


def test_unusable_file_returns_no_data_results(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("garbage" * 200)

    assert [r.status for r in check_data(str(bad), NOW)] == [FAIL]
    assert check_data(str(tmp_path / "nope.db"), NOW) == []


def test_data_checks_do_not_modify_the_file(path):
    before = open(path, "rb").read()

    check_data(path, NOW)

    assert open(path, "rb").read() == before
