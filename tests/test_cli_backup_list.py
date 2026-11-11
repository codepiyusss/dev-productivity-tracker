from datetime import datetime

import pytest

from src.backup import create_backup, format_backup_entry
from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "data" / "t.db"), *argv])

    _run("add", "Write docs")
    _run.root = tmp_path
    return _run


def test_format_backup_entry_readable_backup():
    entry = {
        "created": datetime(2026, 11, 10, 15, 30, 5), "size_bytes": 24576,
        "counts": {"tasks": 12, "time_entries": 3, "goals": 0, "journal_entries": 0},
        "problem": None, "name": "productivity-20261110-153005.db",
    }

    assert format_backup_entry(entry) == (
        "2026-11-10 15:30:05     24 KB  12 tasks, 3 time entries  "
        "[productivity-20261110-153005.db]"
    )


def test_format_backup_entry_unreadable_backup():
    entry = {
        "created": datetime(2026, 11, 10, 15, 30, 5), "size_bytes": 100,
        "counts": None, "problem": "Not a readable database: oops",
        "name": "productivity-20261110-153005.db",
    }

    assert "UNREADABLE (Not a readable database: oops)" in format_backup_entry(entry)


def test_list_with_no_backups(run, capsys):
    capsys.readouterr()

    assert run("backup", "list") == 0

    assert "No backups found in" in capsys.readouterr().out


def test_list_shows_backups_newest_first(run, capsys):
    db = str(run.root / "data" / "t.db")
    folder = run.root / "data" / "backups"
    create_backup(db, folder, datetime(2026, 11, 8, 9, 0, 0))
    create_backup(db, folder, datetime(2026, 11, 10, 9, 0, 0), "weekly")
    capsys.readouterr()

    assert run("backup", "list") == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("Backups in ")
    assert "2026-11-10 09:00:00" in lines[1] and "weekly" in lines[1]
    assert "2026-11-08 09:00:00" in lines[2]
    assert "1 tasks" in lines[1]


def test_list_a_custom_folder(run, capsys):
    other = run.root / "elsewhere"
    run("backup", "create", "--dir", str(other))
    capsys.readouterr()

    run("backup", "list", "--dir", str(other))
    assert "1 tasks" in capsys.readouterr().out

    run("backup", "list")
    assert "No backups found" in capsys.readouterr().out
