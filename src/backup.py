import os
import re
import shutil
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


def verify_database(path) -> list:
    """Check a database file for problems. An empty list means it is healthy.

    Runs SQLite's integrity check and a foreign key check, and confirms the
    file really is a task database. The file is opened read-only.
    """
    problems = []

    try:
        describe_database(path)
    except ValueError as error:
        return [str(error)]

    connection = _open_read_only(path)

    try:
        results = [row[0] for row in connection.execute("PRAGMA integrity_check")]

        if results != ["ok"]:
            problems.extend(f"Integrity check: {line}" for line in results[:5])

        broken = connection.execute("PRAGMA foreign_key_check").fetchall()
        if broken:
            problems.append(
                f"{len(broken)} row(s) point to records that no longer exist."
            )
    except sqlite3.DatabaseError as error:
        problems.append(f"Database error: {error}")
    finally:
        connection.close()

    return problems


def default_backup_dir(db_path) -> Path:
    """Backups live in a 'backups' folder next to the database file."""
    return Path(db_path).parent / "backups"


def create_backup(
    db_path,
    backup_dir=None,
    now: Optional[datetime] = None,
    label: Optional[str] = None
) -> dict:
    """Snapshot the database into the backup folder and verify the result.

    If the new backup fails verification it is deleted and an error is
    raised, so a backup file that exists is always one you can restore.
    """
    now = now or datetime.now()
    folder = Path(backup_dir) if backup_dir else default_backup_dir(db_path)
    destination = folder / backup_filename(now, label)

    path = copy_database(db_path, destination)
    problems = verify_database(path)

    if problems:
        Path(path).unlink()
        raise ValueError("Backup failed verification: " + "; ".join(problems))

    info = describe_database(path)

    return {"path": path, "created": now, **info}


def list_backups(backup_dir) -> list:
    """Backups in a folder, newest first.

    Only files named by `backup_filename` are listed; anything else in the
    folder is ignored. A backup that cannot be read is still listed, with
    `counts` set to None and the reason in `problem`.
    """
    folder = Path(backup_dir)

    if not folder.is_dir():
        return []

    backups = []

    for item in folder.iterdir():
        parsed = parse_backup_name(item.name)

        if parsed is None or not item.is_file():
            continue

        created, label = parsed
        entry = {
            "path": str(item), "name": item.name, "created": created,
            "label": label, "size_bytes": item.stat().st_size,
            "counts": None, "problem": None,
        }

        try:
            entry["counts"] = describe_database(item)["counts"]
        except ValueError as error:
            entry["problem"] = str(error)

        backups.append(entry)

    return sorted(backups, key=lambda entry: (entry["created"], entry["name"]), reverse=True)


PROTECTED_LABELS = ("pre-restore",)


def prune_backups(backup_dir, keep: int) -> list:
    """Delete the oldest backups, keeping the newest `keep`.

    Safety copies made before a restore (label 'pre-restore') are never
    deleted and do not count toward `keep`. Files that are not backups are
    never touched. Returns the names that were removed.
    """
    if isinstance(keep, bool) or not isinstance(keep, int) or keep < 1:
        raise ValueError("Keep must be a whole number of at least 1.")

    candidates = [
        entry for entry in list_backups(backup_dir)
        if entry["label"] not in PROTECTED_LABELS
    ]
    removed = []

    for entry in candidates[keep:]:
        Path(entry["path"]).unlink()
        removed.append(entry["name"])

    return removed


def restore_backup(
    backup_path,
    db_path,
    now: Optional[datetime] = None,
    safety_dir=None
) -> dict:
    """Replace the live database with a backup, safely.

    Order of operations, so a failure at any point leaves the current
    database usable:
      1. The backup is verified. If it has problems nothing is touched.
      2. The current database (if any) is saved as a 'pre-restore' backup.
      3. The backup is copied beside the database, verified again, and then
         moved into place in one step.

    Opening the restored file with `Database` upgrades older backups to the
    current schema automatically.
    """
    backup = Path(backup_path)
    live = Path(db_path)
    now = now or datetime.now()

    problems = verify_database(backup)
    if problems:
        raise ValueError("Backup cannot be restored: " + "; ".join(problems))

    if live.exists() and live.resolve() == backup.resolve():
        raise ValueError("The backup and the live database are the same file.")

    safety_backup = None
    safety_verified = None

    if live.is_file():
        folder = Path(safety_dir) if safety_dir else default_backup_dir(live)

        try:
            safety_backup = create_backup(live, folder, now, "pre-restore")["path"]
            safety_verified = True
        except ValueError as error:
            if "already exists" in str(error):
                raise
            # The current database is damaged. Keep its raw bytes anyway,
            # because it may still be useful, then carry on with the restore.
            folder.mkdir(parents=True, exist_ok=True)
            safety_backup = str(folder / backup_filename(now, "pre-restore"))
            shutil.copyfile(live, safety_backup)
            safety_verified = False

    live.parent.mkdir(parents=True, exist_ok=True)
    staging = live.with_name(live.name + ".restore.tmp")

    try:
        shutil.copyfile(backup, staging)

        staged_problems = verify_database(staging)
        if staged_problems:
            raise ValueError("Copy failed verification: " + "; ".join(staged_problems))

        os.replace(staging, live)
    finally:
        if staging.exists():
            staging.unlink()

    return {
        "restored_from": str(backup),
        "safety_backup": safety_backup,
        "safety_verified": safety_verified,
        **describe_database(live),
    }
