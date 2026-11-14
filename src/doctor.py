import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.backup import _open_read_only, verify_database

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
