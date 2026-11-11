import os

import pytest

from src.backup import list_backups
from src.database import Database
from src.main import main


@pytest.fixture
def setup(tmp_path):
    db = str(tmp_path / "data" / "t.db")
    main(["--db", db, "add", "Existing"])
    csv_file = tmp_path / "in.csv"
    csv_file.write_text("title\nImported A\nImported B\n", encoding="utf-8")
    return db, str(csv_file), tmp_path / "data" / "backups"


def titles(db):
    return sorted(t.title for t in Database(db).get_all_tasks())


def test_import_with_backup_saves_the_state_before_importing(setup, capsys):
    db, csv_file, folder = setup
    capsys.readouterr()

    assert main(["--db", db, "import", csv_file, "--backup"]) == 0

    output = capsys.readouterr().out
    assert "Backup saved before import:" in output
    assert "Imported 2 task(s)." in output
    assert titles(db) == ["Existing", "Imported A", "Imported B"]

    backup = list_backups(folder)[0]
    assert backup["label"] == "before-import"
    assert titles(backup["path"]) == ["Existing"]   # the state before importing


def test_the_backup_can_undo_the_import(setup):
    db, csv_file, folder = setup
    main(["--db", db, "import", csv_file, "--backup"])
    backup = list_backups(folder)[0]["path"]

    main(["--db", db, "backup", "restore", backup, "--yes"])

    assert titles(db) == ["Existing"]


def test_import_without_the_flag_makes_no_backup(setup):
    db, csv_file, folder = setup

    main(["--db", db, "import", csv_file])

    assert not folder.exists()


def test_dry_run_never_makes_a_backup(setup, capsys):
    db, csv_file, folder = setup
    capsys.readouterr()

    assert main(["--db", db, "import", csv_file, "--dry-run", "--backup"]) == 0

    assert "Backup saved" not in capsys.readouterr().out
    assert not folder.exists()
    assert titles(db) == ["Existing"]


def test_failed_import_still_returns_an_error_code(setup, tmp_path, capsys):
    db, _, _ = setup

    assert main(["--db", db, "import", str(tmp_path / "missing.csv")]) == 1


def test_backup_failure_stops_the_import(setup, monkeypatch, capsys):
    db, csv_file, _ = setup

    def broken(*args, **kwargs):
        raise ValueError("disk full")

    monkeypatch.setattr("src.main.create_backup", broken)
    capsys.readouterr()

    assert main(["--db", db, "import", csv_file, "--backup"]) == 1

    assert "Backup failed, so nothing was imported: disk full" in capsys.readouterr().out
    assert titles(db) == ["Existing"]
