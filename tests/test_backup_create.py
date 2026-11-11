import os
from datetime import datetime
from pathlib import Path

import pytest

from src.backup import create_backup, default_backup_dir, parse_backup_name
from src.database import Database
from src.tasks import TaskManager

NOW = datetime(2026, 11, 10, 15, 30, 5)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "data" / "productivity.db")
    manager = TaskManager(Database(path))
    manager.create_task("A")
    manager.create_task("B")
    return path


def test_default_backup_dir_is_next_to_the_database():
    assert default_backup_dir("data/productivity.db") == Path("data/backups")


def test_create_backup_in_the_default_folder(db_path):
    info = create_backup(db_path, now=NOW)

    assert info["path"].endswith("productivity-20261110-153005.db")
    assert Path(info["path"]).parent == Path(db_path).parent / "backups"
    assert info["counts"]["tasks"] == 2
    assert info["size_bytes"] > 0
    assert info["created"] == NOW


def test_create_backup_in_a_chosen_folder_with_label(db_path, tmp_path):
    info = create_backup(db_path, tmp_path / "elsewhere", NOW, "Before Upgrade")

    assert Path(info["path"]).parent == tmp_path / "elsewhere"
    assert parse_backup_name(Path(info["path"]).name) == (NOW, "before-upgrade")


def test_backup_contains_the_data_and_leaves_the_original_alone(db_path):
    before = open(db_path, "rb").read()

    info = create_backup(db_path, now=NOW)

    assert sorted(t.title for t in Database(info["path"]).get_all_tasks()) == ["A", "B"]
    assert open(db_path, "rb").read() == before


def test_two_backups_in_the_same_second_do_not_overwrite(db_path):
    create_backup(db_path, now=NOW)

    with pytest.raises(ValueError, match="already exists"):
        create_backup(db_path, now=NOW)


def test_backups_with_different_times_coexist(db_path):
    create_backup(db_path, now=NOW)
    create_backup(db_path, now=datetime(2026, 11, 10, 15, 30, 6))

    assert len(os.listdir(default_backup_dir(db_path))) == 2


def test_missing_database_is_rejected_and_nothing_is_created(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        create_backup(str(tmp_path / "nope.db"), now=NOW)

    assert not (tmp_path / "backups").exists()


def test_no_temporary_files_are_left_behind(db_path):
    create_backup(db_path, now=NOW)

    names = os.listdir(default_backup_dir(db_path))
    assert not any(name.endswith(".tmp") for name in names)


def test_failed_verification_removes_the_backup(db_path, monkeypatch):
    monkeypatch.setattr("src.backup.verify_database", lambda path: ["something is wrong"])

    with pytest.raises(ValueError, match="failed verification: something is wrong"):
        create_backup(db_path, now=NOW)

    assert os.listdir(default_backup_dir(db_path)) == []
