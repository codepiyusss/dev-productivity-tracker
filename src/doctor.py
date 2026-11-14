import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from typing import List

from src.backup import _open_read_only, verify_database
from src.timetracking import STALE_AFTER_SECONDS, TIMESTAMP_FORMAT
from src.utils import validate_due_date

OK, WARN, FAIL, INFO = "ok", "warn", "fail", "info"
REQUIRED_TABLES = (
    "tasks", "task_tags", "time_entries", "goals", "task_dependencies",
)


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def check_database(db_path) -> CheckResult:
    """Does the file exist, open, and pass SQLite's own integrity checks?"""
    if not Path(db_path).is_file():
        return CheckResult(
            "Database file", FAIL,
            f"{db_path} does not exist yet. Run any command to create it."
        )

    problems = verify_database(db_path)

    if problems:
        return CheckResult("Database file", FAIL, "; ".join(problems))

    return CheckResult("Database file", OK, f"{db_path} opens and passes integrity checks.")


def check_schema(db_path) -> CheckResult:
    """Are all the tables this version of the tool expects present?"""
    try:
        connection = _open_read_only(db_path)
    except ValueError as error:
        return CheckResult("Schema", FAIL, str(error))

    try:
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    except sqlite3.DatabaseError as error:
        return CheckResult("Schema", FAIL, f"Could not read the schema: {error}")
    finally:
        connection.close()

    missing = [table for table in REQUIRED_TABLES if table not in tables]

    if missing:
        return CheckResult(
            "Schema", WARN,
            "Missing tables: " + ", ".join(missing)
            + ". They are created automatically the next time you run a command."
        )

    return CheckResult("Schema", OK, "All expected tables are present.")


def has_failures(results: List[CheckResult]) -> bool:
    return any(result.status == FAIL for result in results)


def _query(connection, sql):
    """Run a query, or return None if a table or column is missing."""
    try:
        return connection.execute(sql).fetchall()
    except sqlite3.OperationalError:
        return None


def check_data(db_path, now: Optional[datetime] = None) -> List[CheckResult]:
    """Look for data that is odd but not corrupt. Nothing is modified."""
    now = now or datetime.now()

    try:
        connection = _open_read_only(db_path)
    except ValueError:
        return []   # check_database already reports an unusable file

    results = []

    try:
        rows = _query(
            connection,
            "SELECT task_id, due_date FROM tasks "
            "WHERE due_date IS NOT NULL AND TRIM(due_date) != ''"
        ) or []
        bad_dates = []
        for task_id, due_date in rows:
            try:
                validate_due_date(due_date)
            except ValueError:
                bad_dates.append(task_id)
        results.append(
            CheckResult("Due dates", WARN,
                        f"{len(bad_dates)} task(s) have unreadable due dates "
                        f"(IDs: {', '.join(map(str, bad_dates[:10]))}). "
                        "Fix them with: edit ID --due-date YYYY-MM-DD")
            if bad_dates else CheckResult("Due dates", OK, "All due dates are valid.")
        )

        rows = _query(
            connection,
            "SELECT COUNT(*) FROM tasks WHERE recurrence IS NOT NULL "
            "AND (due_date IS NULL OR TRIM(due_date) = '')"
        )
        broken = rows[0][0] if rows else 0
        results.append(
            CheckResult("Repeating tasks", WARN,
                        f"{broken} repeating task(s) have no due date, so they cannot repeat.")
            if broken else CheckResult("Repeating tasks", OK, "All repeating tasks have due dates.")
        )

        rows = _query(connection, "SELECT started_at FROM time_entries WHERE ended_at IS NULL")
        if rows:
            started = datetime.strptime(rows[0][0], TIMESTAMP_FORMAT)
            age = (now - started).total_seconds()
            if age >= STALE_AFTER_SECONDS:
                results.append(CheckResult(
                    "Timer", WARN,
                    f"A timer has been running for {int(age // 3600)} hours. "
                    "Stop it with: timer stop"
                ))
            else:
                results.append(CheckResult("Timer", OK, "A timer is running normally."))
        else:
            results.append(CheckResult("Timer", OK, "No timer is running."))

        rows = _query(
            connection,
            "SELECT COUNT(*) FROM tasks WHERE completed = 1 AND completed_at IS NULL"
        )
        legacy = rows[0][0] if rows else 0
        if legacy:
            results.append(CheckResult(
                "Completion times", INFO,
                f"{legacy} completed task(s) have no completion time (they were "
                "finished before time tracking). They do not count toward goals or streaks."
            ))
    except sqlite3.DatabaseError as error:
        results.append(CheckResult("Data", FAIL, f"Could not read tasks: {error}"))
    finally:
        connection.close()

    return results
