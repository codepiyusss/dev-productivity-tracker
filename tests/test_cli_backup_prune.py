from datetime import datetime

import pytest

from src.backup import backups_to_prune, create_backup, list_backups
from src.database import Database
from src.main import main
from src.tasks import TaskManager


def make(tmp_path, count=5, extra=None):
    db = str(tmp_path / "data" / "t.db")
    TaskManager(Database(db)).create_task("A")
    folder = tmp_path / "data" / "backups"
    for day in range(1, count + 1):
        create_backup(db, folder, datetime(2026, 11, day, 9, 0, 0))
    if extra:
        create_backup(db, folder, *extra)
    return db, folder


def run(db, *argv):
    return main(["--db", db, *argv])


def test_backups_to_prune_changes_nothing(tmp_path):
    _, folder = make(tmp_path)

    doomed = backups_to_prune(folder, 2)

    assert [e["created"].day for e in doomed] == [3, 2, 1]
    assert len(list_backups(folder)) == 5


def test_backups_to_prune_validates_keep(tmp_path):
    _, folder = make(tmp_path)

    with pytest.raises(ValueError, match="at least 1"):
        backups_to_prune(folder, 0)


def test_prune_with_yes_deletes_the_oldest(tmp_path, capsys):
    db, folder = make(tmp_path)
    capsys.readouterr()

    assert run(db, "backup", "prune", "--keep", "2", "--yes") == 0

    output = capsys.readouterr().out
    assert "Would delete 3 old backup(s), keeping the newest 2:" in output
    assert "Deleted 3 backup(s)." in output
    assert [b["created"].day for b in list_backups(folder)] == [5, 4]


def test_prune_asks_first_and_cancels_by_default(tmp_path, capsys, monkeypatch):
    db, folder = make(tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    capsys.readouterr()

    assert run(db, "backup", "prune", "--keep", "2") == 0

    assert "Cancelled. Nothing was deleted." in capsys.readouterr().out
    assert len(list_backups(folder)) == 5


def test_prune_when_nothing_to_delete_never_prompts(tmp_path, capsys, monkeypatch):
    db, _ = make(tmp_path, count=3)
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("prompted"))
    capsys.readouterr()

    assert run(db, "backup", "prune", "--keep", "5") == 0

    assert "Nothing to delete." in capsys.readouterr().out


def test_prune_never_deletes_safety_copies(tmp_path, capsys):
    db, folder = make(tmp_path, extra=(datetime(2026, 10, 1, 9, 0, 0), "pre-restore"))

    run(db, "backup", "prune", "--keep", "1", "--yes")

    names = sorted(b["name"] for b in list_backups(folder))
    assert names == [
        "productivity-20261001-090000-pre-restore.db",
        "productivity-20261105-090000.db",
    ]


def test_prune_default_keeps_five(tmp_path, capsys):
    db, folder = make(tmp_path, count=7)

    run(db, "backup", "prune", "--yes")

    assert len(list_backups(folder)) == 5


def test_prune_rejects_a_bad_keep_value_at_parse_time(tmp_path, capsys):
    db, _ = make(tmp_path, count=2)

    with pytest.raises(SystemExit):
        run(db, "backup", "prune", "--keep", "0")
