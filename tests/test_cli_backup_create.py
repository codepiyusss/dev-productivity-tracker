import os
from pathlib import Path

import pytest

from src.backup import format_size
from src.database import Database
from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "data" / "t.db"), *argv])

    _run("add", "Write docs")
    _run("add", "Fix bug")
    _run.root = tmp_path
    return _run


@pytest.mark.parametrize("size, expected", [
    (0, "0 B"), (512, "512 B"), (1024, "1 KB"), (1536, "1.5 KB"),
    (24576, "24 KB"), (1048576, "1 MB"), (1572864, "1.5 MB"), (5 * 1024**3, "5 GB"),
])
def test_format_size(size, expected):
    assert format_size(size) == expected


def test_backup_create_saves_a_verified_copy(run, capsys):
    capsys.readouterr()

    assert run("backup", "create") == 0

    output = capsys.readouterr().out
    assert "Backup created:" in output
    assert "Contents: 2 tasks (" in output
    files = os.listdir(run.root / "data" / "backups")
    assert len(files) == 1 and files[0].startswith("productivity-")


def test_label_and_custom_folder(run, capsys):
    folder = run.root / "elsewhere"

    assert run("backup", "create", "--label", "Before Upgrade", "--dir", str(folder)) == 0

    assert os.listdir(folder)[0].endswith("-before-upgrade.db")


def test_backup_holds_the_current_data(run, capsys):
    run("backup", "create")
    capsys.readouterr()
    backup = next((run.root / "data" / "backups").iterdir())

    assert sorted(t.title for t in Database(str(backup)).get_all_tasks()) == [
        "Fix bug", "Write docs"
    ]


def test_backup_of_a_missing_database_reports_the_problem(tmp_path, capsys):
    from src.main import main as cli_main
    code = cli_main(["--db", str(tmp_path / "x" / "t.db"), "backup", "create", "--dir", str(tmp_path / "out")])

    # The database file is created on first use, so this still succeeds.
    assert code == 0
    assert "Backup created:" in capsys.readouterr().out


def test_second_backup_in_the_same_second_fails_cleanly(run, capsys, monkeypatch):
    from datetime import datetime
    import src.backup as backup_module

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 10, 9, 0, 0)

    monkeypatch.setattr(backup_module, "datetime", FixedDatetime)
    assert run("backup", "create") == 0
    capsys.readouterr()

    assert run("backup", "create") == 1
    assert "Backup failed:" in capsys.readouterr().out
