import sqlite3
import sys
from datetime import datetime

import pytest

from src.backup import create_backup
from src.database import Database
from src.doctor import (
    FAIL, INFO, OK, WARN, check_backups, check_environment, has_failures, run_checks,
)
from src.tasks import TaskManager

NOW = datetime(2026, 11, 10, 12, 0, 0)


@pytest.fixture
def path(tmp_path):
    p = str(tmp_path / "data" / "t.db")
    TaskManager(Database(p)).create_task("A")
    return p


def test_no_backups_is_a_warning_with_the_fix(path):
    result = check_backups(path, NOW)

    assert result.status == WARN and "backup create" in result.detail


def test_recent_backup_is_fine(path):
    create_backup(path, now=datetime(2026, 11, 10, 9, 0, 0))

    result = check_backups(path, NOW)

    assert result.status == OK and "today" in result.detail and "1 saved" in result.detail


def test_old_backup_is_a_warning(path):
    create_backup(path, now=datetime(2026, 9, 1, 9, 0, 0))

    result = check_backups(path, NOW)

    assert result.status == WARN and "70 days old" in result.detail


def test_exactly_thirty_days_is_still_fine(path):
    create_backup(path, now=datetime(2026, 10, 11, 12, 0, 0))

    assert check_backups(path, NOW).status == OK


def test_safety_copies_do_not_count_as_real_backups(path):
    create_backup(path, now=datetime(2026, 11, 10, 9, 0, 0), label="pre-restore")

    assert check_backups(path, NOW).status == WARN


def test_environment_reports_versions():
    result = check_environment()

    assert result.status == INFO
    assert f"Python {sys.version_info[0]}.{sys.version_info[1]}" in result.detail
    assert f"SQLite {sqlite3.sqlite_version}" in result.detail


def test_run_checks_returns_everything_in_order(path):
    create_backup(path, now=datetime(2026, 11, 10, 9, 0, 0))

    results = run_checks(path, NOW)

    names = [r.name for r in results]
    assert names[:2] == ["Database file", "Schema"]
    assert names[-2:] == ["Backups", "Environment"]
    assert "Due dates" in names and "Timer" in names
    assert not has_failures(results)


def test_run_checks_on_a_missing_database(tmp_path):
    results = run_checks(str(tmp_path / "nope.db"), NOW)

    assert results[0].status == FAIL
    assert has_failures(results)


def test_run_checks_on_a_corrupt_database_does_not_crash(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("garbage" * 300)

    results = run_checks(str(bad), NOW)

    assert has_failures(results)
    assert results[-1].name == "Environment"
