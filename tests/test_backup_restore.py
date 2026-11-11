import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from src.backup import create_backup, list_backups, restore_backup
from src.database import Database
from src.tasks import TaskManager

NOW = datetime(2026, 11, 10, 15, 30, 5)


def titles(path):
    return sorted(t.title for t in Database(str(path)).get_all_tasks())


@pytest.fixture
def setup(tmp_path):
    live = tmp_path / "data" / "productivity.db"
    manager = TaskManager(Database(str(live)))
    manager.create_task("Original A")
    manager.create_task("Original B")
    backup = create_backup(str(live), tmp_path / "b", datetime(2026, 11, 1, 9, 0, 0))["path"]
    manager.create_task("Added after backup")
    manager.delete_task(1)
    return live, backup, tmp_path


def test_restore_brings_back_the_backed_up_data(setup):
    live, backup, _ = setup

    result = restore_backup(backup, str(live), now=NOW)

    assert titles(live) == ["Original A", "Original B"]
    assert result["counts"]["tasks"] == 2
    assert result["restored_from"] == backup


def test_restore_first_saves_the_current_database(setup):
    live, backup, _ = setup

    result = restore_backup(backup, str(live), now=NOW)

    assert result["safety_verified"] is True
    assert titles(result["safety_backup"]) == ["Added after backup", "Original B"]
    assert result["safety_backup"].endswith("productivity-20261110-153005-pre-restore.db")


def test_bad_backup_is_rejected_and_nothing_changes(setup):
    live, _, tmp_path = setup
    bad = tmp_path / "productivity-20261101-090000.db"
    bad.write_text("garbage" * 100)
    before = live.read_bytes()

    with pytest.raises(ValueError, match="cannot be restored"):
        restore_backup(str(bad), str(live), now=NOW)

    assert live.read_bytes() == before
    assert not (live.parent / "backups").exists()


def test_missing_backup_is_rejected(setup):
    live, _, tmp_path = setup

    with pytest.raises(ValueError, match="not found"):
        restore_backup(str(tmp_path / "nope.db"), str(live), now=NOW)


def test_restoring_the_live_file_onto_itself_is_rejected(setup):
    live, _, _ = setup

    with pytest.raises(ValueError, match="same file"):
        restore_backup(str(live), str(live), now=NOW)


def test_restore_works_when_there_is_no_current_database(setup):
    _, backup, tmp_path = setup
    fresh = tmp_path / "newmachine" / "productivity.db"

    result = restore_backup(backup, str(fresh), now=NOW)

    assert titles(fresh) == ["Original A", "Original B"]
    assert result["safety_backup"] is None


def test_damaged_current_database_is_kept_as_raw_safety_copy(setup):
    live, backup, _ = setup
    live.write_bytes(b"corrupt" * 200)

    result = restore_backup(backup, str(live), now=NOW)

    assert result["safety_verified"] is False
    assert Path(result["safety_backup"]).read_bytes() == b"corrupt" * 200
    assert titles(live) == ["Original A", "Original B"]


def test_no_temporary_files_remain(setup):
    live, backup, _ = setup

    restore_backup(backup, str(live), now=NOW)

    assert not any(name.endswith(".tmp") for name in os.listdir(live.parent))


def test_failed_copy_verification_leaves_the_live_database_untouched(setup, monkeypatch):
    live, backup, _ = setup
    before = live.read_bytes()
    calls = {"count": 0}
    real = __import__("src.backup", fromlist=["verify_database"]).verify_database

    def flaky(path):
        calls["count"] += 1
        # Healthy on the first checks (backup, safety copy), broken on the staged copy.
        return real(path) if "restore.tmp" not in str(path) else ["staged copy is bad"]

    monkeypatch.setattr("src.backup.verify_database", flaky)

    with pytest.raises(ValueError, match="Copy failed verification"):
        restore_backup(backup, str(live), now=NOW)

    assert live.read_bytes() == before


def test_restored_old_backup_is_upgraded_when_opened(tmp_path):
    old = tmp_path / "productivity-20260101-090000.db"
    connection = sqlite3.connect(str(old))
    with connection:
        connection.execute("""
            CREATE TABLE tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                description TEXT DEFAULT '', priority TEXT NOT NULL DEFAULT 'medium',
                category TEXT NOT NULL DEFAULT 'general', due_date TEXT,
                completed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            )""")
        connection.execute("INSERT INTO tasks (title, created_at) VALUES ('Ancient', '2026-01-01T00:00:00')")
    connection.close()
    live = tmp_path / "live" / "productivity.db"

    restore_backup(str(old), str(live), now=NOW)
    manager = TaskManager(Database(str(live)))

    task = manager.get_all_tasks()[0]
    assert (task.title, task.recurrence, task.completed_at) == ("Ancient", None, None)
    manager.create_task("New", due_date="2026-12-01", recurrence="weekly")
    manager.database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")


def test_safety_copy_appears_in_the_backup_list(setup):
    live, backup, _ = setup

    restore_backup(backup, str(live), now=NOW)

    labels = [b["label"] for b in list_backups(live.parent / "backups")]
    assert labels == ["pre-restore"]
