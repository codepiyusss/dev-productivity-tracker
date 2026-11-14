import sqlite3

from src.database import Database
from src.doctor import FAIL, OK, WARN, check_database, check_schema, has_failures, CheckResult
from src.tasks import TaskManager


def healthy(tmp_path):
    path = str(tmp_path / "t.db")
    TaskManager(Database(path)).create_task("A")
    return path


def test_healthy_database_passes(tmp_path):
    result = check_database(healthy(tmp_path))

    assert result.status == OK and "integrity" in result.detail


def test_missing_file_fails_with_a_helpful_message(tmp_path):
    result = check_database(str(tmp_path / "nope.db"))

    assert result.status == FAIL and "does not exist yet" in result.detail


def test_garbage_file_fails(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("garbage" * 200)

    result = check_database(str(bad))

    assert result.status == FAIL and "Not a readable database" in result.detail


def test_schema_ok_for_a_current_database(tmp_path):
    assert check_schema(healthy(tmp_path)).status == OK


def test_schema_warns_about_missing_tables(tmp_path):
    path = healthy(tmp_path)
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("DROP TABLE time_entries")
        connection.execute("DROP TABLE task_dependencies")
    connection.close()

    result = check_schema(path)

    assert result.status == WARN
    assert "time_entries" in result.detail and "task_dependencies" in result.detail
    assert "created automatically" in result.detail


def test_schema_fails_for_unreadable_file(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("garbage" * 200)

    assert check_schema(str(bad)).status == FAIL
    assert check_schema(str(tmp_path / "nope.db")).status == FAIL


def test_checks_never_modify_the_database(tmp_path):
    path = healthy(tmp_path)
    before = open(path, "rb").read()

    check_database(path)
    check_schema(path)

    assert open(path, "rb").read() == before


def test_has_failures():
    assert has_failures([CheckResult("a", OK, ""), CheckResult("b", FAIL, "")]) is True
    assert has_failures([CheckResult("a", OK, ""), CheckResult("b", WARN, "")]) is False
    assert has_failures([]) is False
