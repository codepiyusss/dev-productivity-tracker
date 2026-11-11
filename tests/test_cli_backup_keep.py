from datetime import datetime

import pytest

from src.backup import create_backup, list_backups
from src.database import Database
from src.main import main
from src.tasks import TaskManager


@pytest.fixture
def setup(tmp_path):
    db = str(tmp_path / "data" / "t.db")
    TaskManager(Database(db)).create_task("A")
    folder = tmp_path / "data" / "backups"
    for day in range(1, 5):
        create_backup(db, folder, datetime(2026, 1, day, 9, 0, 0))
    return db, folder


def test_keep_removes_older_backups_after_creating(setup, capsys):
    db, folder = setup
    capsys.readouterr()

    assert main(["--db", db, "backup", "create", "--keep", "3"]) == 0

    output = capsys.readouterr().out
    assert "Backup created:" in output
    assert "Removed 2 old backup(s); keeping the newest 3." in output
    backups = list_backups(folder)
    assert len(backups) == 3
    # The brand-new backup is the newest, so it is always kept.
    assert backups[0]["created"].year == datetime.now().year


def test_keep_larger_than_the_count_removes_nothing(setup, capsys):
    db, folder = setup
    capsys.readouterr()

    main(["--db", db, "backup", "create", "--keep", "10"])

    assert "Removed" not in capsys.readouterr().out
    assert len(list_backups(folder)) == 5


def test_without_keep_nothing_is_ever_deleted(setup):
    db, folder = setup

    main(["--db", db, "backup", "create"])

    assert len(list_backups(folder)) == 5


def test_keep_does_not_touch_safety_copies(setup, capsys):
    db, folder = setup
    create_backup(db, folder, datetime(2025, 12, 1, 9, 0, 0), "pre-restore")

    main(["--db", db, "backup", "create", "--keep", "1"])

    labels = [b["label"] for b in list_backups(folder)]
    assert "pre-restore" in labels
    assert len(labels) == 2


def test_keep_zero_is_rejected(setup):
    db, _ = setup

    with pytest.raises(SystemExit):
        main(["--db", db, "backup", "create", "--keep", "0"])
