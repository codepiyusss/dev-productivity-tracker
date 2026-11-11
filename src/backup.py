import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

PREFIX = "productivity-"
EXTENSION = ".db"
TIME_FORMAT = "%Y%m%d-%H%M%S"
MAX_LABEL_LENGTH = 30

_NAME_PATTERN = re.compile(
    r"^productivity-(\d{8}-\d{6})(?:-([a-z0-9-]+))?\.db$"
)


def clean_label(label: Optional[str]) -> Optional[str]:
    """Make a label safe for use in a file name, or None if nothing is left."""
    if not label:
        return None

    cleaned = re.sub(r"[^a-z0-9]+", "-", str(label).casefold()).strip("-")
    cleaned = cleaned[:MAX_LABEL_LENGTH].strip("-")

    return cleaned or None


def backup_filename(now: Optional[datetime] = None, label: Optional[str] = None) -> str:
    """File name such as 'productivity-20261110-153000-before-import.db'."""
    name = PREFIX + (now or datetime.now()).strftime(TIME_FORMAT)
    label = clean_label(label)

    if label:
        name += f"-{label}"

    return name + EXTENSION


def parse_backup_name(name: str):
    """Return (created: datetime, label or None) for a backup file name.

    Returns None for any file that was not named by `backup_filename`.
    """
    match = _NAME_PATTERN.match(name)

    if not match:
        return None

    try:
        created = datetime.strptime(match.group(1), TIME_FORMAT)
    except ValueError:
        return None

    return created, match.group(2)


def copy_database(source_path, dest_path) -> str:
    """Write a consistent snapshot of a SQLite database to a new file.

    Uses SQLite's own backup API, so the copy is valid even if the source
    is being written to. The snapshot is built in a temporary file and moved
    into place, so an interrupted copy never leaves a half-written backup.
    Refuses to overwrite an existing file.
    """
    source = Path(source_path)
    dest = Path(dest_path)

    if not source.is_file():
        raise ValueError(f"Database file not found: {source}")

    if dest.exists():
        raise ValueError(f"File already exists: {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(dest.name + ".tmp")

    if temp.exists():
        temp.unlink()

    try:
        origin = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
        target = sqlite3.connect(str(temp))
        try:
            origin.backup(target)
        finally:
            target.close()
            origin.close()

        os.replace(temp, dest)
    except sqlite3.Error as error:
        if temp.exists():
            temp.unlink()
        raise ValueError(f"Could not copy database: {error}")

    return str(dest)


COUNTED_TABLES = {
    "tasks": "tasks",
    "time_entries": "time entries",
    "goals": "goals",
    "journal_entries": "journal entries",
}


def _open_read_only(path) -> sqlite3.Connection:
    source = Path(path)

    if not source.is_file():
        raise ValueError(f"Database file not found: {source}")

    return sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)


def describe_database(path) -> dict:
    """What a database file contains, without changing it.

    Returns {"size_bytes": int, "counts": {table: rows}}. Tables that do not
    exist yet (for example, time entries in an older database) count as 0.
    Raises ValueError if the file is not a task database.
    """
    connection = _open_read_only(path)

    try:
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        if "tasks" not in tables:
            raise ValueError("This file does not look like a tracker database.")

        counts = {
            table: (
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                if table in tables else 0
            )
            for table in COUNTED_TABLES
        }
    except sqlite3.DatabaseError as error:
        raise ValueError(f"Not a readable database: {error}")
    finally:
        connection.close()

    return {"size_bytes": Path(path).stat().st_size, "counts": counts}


def format_counts(counts: dict) -> str:
    """'12 tasks, 3 time entries, 1 goals, 5 journal entries' (zeros omitted)."""
    parts = [
        f"{counts[table]} {label}"
        for table, label in COUNTED_TABLES.items()
        if counts.get(table)
    ]

    return ", ".join(parts) if parts else "empty"
