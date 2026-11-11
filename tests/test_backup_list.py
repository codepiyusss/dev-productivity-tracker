from datetime import datetime

import pytest

from src.backup import create_backup, list_backups
from src.database import Database
from src.tasks import TaskManager


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "productivity.db")
    TaskManager(Database(path)).create_task("A")
    return path


def test_missing_folder_gives_an_empty_list(tmp_path):
    assert list_backups(tmp_path / "nope") == []


def test_empty_folder_gives_an_empty_list(tmp_path):
    assert list_backups(tmp_path) == []


def test_backups_are_listed_newest_first(db_path, tmp_path):
    folder = tmp_path / "b"
    create_backup(db_path, folder, datetime(2026, 11, 8, 9, 0, 0))
    create_backup(db_path, folder, datetime(2026, 11, 10, 9, 0, 0), "weekly")
    create_backup(db_path, folder, datetime(2026, 11, 9, 9, 0, 0))

    backups = list_backups(folder)

    assert [b["created"].day for b in backups] == [10, 9, 8]
    assert backups[0]["label"] == "weekly"
    assert backups[1]["label"] is None


def test_listing_includes_size_and_counts(db_path, tmp_path):
    create_backup(db_path, tmp_path / "b", datetime(2026, 11, 8, 9, 0, 0))

    backup = list_backups(tmp_path / "b")[0]

    assert backup["size_bytes"] > 0
    assert backup["counts"]["tasks"] == 1
    assert backup["problem"] is None
    assert backup["name"] == "productivity-20261108-090000.db"


def test_unrelated_files_and_folders_are_ignored(db_path, tmp_path):
    folder = tmp_path / "b"
    create_backup(db_path, folder, datetime(2026, 11, 8, 9, 0, 0))
    (folder / "notes.txt").write_text("hi")
    (folder / "productivity.db").write_text("not a backup name")
    (folder / "productivity-20261108-090001.db.tmp").write_text("partial")
    (folder / "productivity-20261108-090002.db").mkdir()

    assert [b["name"] for b in list_backups(folder)] == ["productivity-20261108-090000.db"]


def test_unreadable_backup_is_listed_with_its_problem(tmp_path):
    folder = tmp_path / "b"
    folder.mkdir()
    (folder / "productivity-20261108-090000.db").write_text("garbage" * 100)

    backup = list_backups(folder)[0]

    assert backup["counts"] is None
    assert "Not a readable database" in backup["problem"]
