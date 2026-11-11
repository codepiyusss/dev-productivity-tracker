from datetime import datetime
from pathlib import Path

import pytest

from src.backup import create_backup, list_backups, prune_backups
from src.database import Database
from src.tasks import TaskManager


@pytest.fixture
def folder(tmp_path):
    db = str(tmp_path / "productivity.db")
    TaskManager(Database(db)).create_task("A")
    target = tmp_path / "b"
    for day in range(1, 6):
        create_backup(db, target, datetime(2026, 11, day, 9, 0, 0))
    return target


def days(folder):
    return sorted(b["created"].day for b in list_backups(folder))


def test_prune_keeps_the_newest(folder):
    removed = prune_backups(folder, keep=2)

    assert days(folder) == [4, 5]
    assert sorted(removed) == [
        "productivity-20261101-090000.db",
        "productivity-20261102-090000.db",
        "productivity-20261103-090000.db",
    ]


def test_prune_does_nothing_when_there_are_few_enough(folder):
    assert prune_backups(folder, keep=10) == []
    assert days(folder) == [1, 2, 3, 4, 5]


def test_prune_keep_one(folder):
    prune_backups(folder, keep=1)

    assert days(folder) == [5]


def test_safety_copies_are_never_deleted_or_counted(folder, tmp_path):
    db = str(tmp_path / "productivity.db")
    create_backup(db, folder, datetime(2026, 10, 1, 9, 0, 0), "pre-restore")

    prune_backups(folder, keep=1)

    names = sorted(b["name"] for b in list_backups(folder))
    assert names == [
        "productivity-20261001-090000-pre-restore.db",  # protected
        "productivity-20261105-090000.db",              # the one kept
    ]


def test_other_files_are_never_touched(folder):
    (folder / "notes.txt").write_text("keep me")
    (folder / "productivity.db").write_text("also keep me")

    prune_backups(folder, keep=1)

    assert (folder / "notes.txt").read_text() == "keep me"
    assert (folder / "productivity.db").read_text() == "also keep me"


def test_missing_folder_is_fine(tmp_path):
    assert prune_backups(tmp_path / "nope", keep=3) == []


@pytest.mark.parametrize("keep", [0, -1, 2.5, "3", True])
def test_invalid_keep_values_are_rejected_before_deleting(folder, keep):
    with pytest.raises(ValueError, match="at least 1"):
        prune_backups(folder, keep)

    assert days(folder) == [1, 2, 3, 4, 5]
