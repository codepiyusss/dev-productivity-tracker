import pytest

from src.database import Database
from src.main import main
from src.models.task import Task


@pytest.fixture
def run(tmp_path):
    db = str(tmp_path / "data" / "t.db")

    def _run(*argv):
        return main(["--db", db, *argv])

    _run.db = db
    _run.root = tmp_path
    return _run


def test_goal_target_wording(run, capsys):
    run("goal", "set", "daily", "1")
    run("goal", "set", "weekly", "5")

    output = capsys.readouterr().out
    assert "Daily goal set to 1 task." in output
    assert "Weekly goal set to 5 tasks." in output


def test_export_wording(run, capsys):
    run("add", "Only task")
    capsys.readouterr()

    run("export", "--output", str(run.root / "one.csv"))
    run("add", "Second task")
    capsys.readouterr()
    run("export", "--output", str(run.root / "two.csv"))

    assert "Exported 2 tasks to:" in capsys.readouterr().out


def test_single_task_export_is_singular(run, capsys):
    run("add", "Only task")
    capsys.readouterr()

    run("export", "--output", str(run.root / "one.csv"))

    assert "Exported 1 task to:" in capsys.readouterr().out


def test_import_wording_singular_and_plural(run, capsys):
    one = run.root / "one.csv"
    one.write_text("title\nA\n", encoding="utf-8")
    two = run.root / "two.csv"
    two.write_text("title\nB\nC\n,\n", encoding="utf-8")
    capsys.readouterr()

    run("import", str(one))
    assert "Imported 1 task." in capsys.readouterr().out

    run("import", str(two))
    output = capsys.readouterr().out
    assert "Imported 2 tasks." in output
    assert "Skipped 1 invalid row:" in output


def test_import_duplicate_wording(run, capsys):
    csv_file = run.root / "in.csv"
    csv_file.write_text("title\nA\n", encoding="utf-8")
    run("import", str(csv_file))
    capsys.readouterr()

    run("import", str(csv_file))

    assert "Skipped 1 duplicate task." in capsys.readouterr().out


def test_purge_wording_for_one_task(run, capsys):
    run("add", "Recent")
    Database(run.db).add_task(
        Task("Ancient", completed=True, completed_at="2020-01-01T09:00:00")
    )
    capsys.readouterr()

    run("purge", "--older-than", "30", "--dry-run")

    output = capsys.readouterr().out
    assert "1 completed task finished 30+ days ago would be deleted:" in output
    assert "0 time entries and 0 dependency links." in output


def test_one_day_of_time_entries(run, capsys):
    capsys.readouterr()

    run("timer", "list", "--days", "1")

    assert "No time entries in the last 1 day." in capsys.readouterr().out


def test_time_summary_for_one_day(run, capsys):
    capsys.readouterr()

    run("timer", "summary", "--days", "1")

    assert "Time tracked in the last 1 day: 0s (0 entries)" in capsys.readouterr().out


def test_backup_prune_and_keep_wording_for_one_backup(run, capsys):
    run("add", "x")
    from datetime import datetime
    from src.backup import create_backup
    folder = run.root / "data" / "backups"
    create_backup(run.db, folder, datetime(2026, 1, 1, 9, 0, 0))
    create_backup(run.db, folder, datetime(2026, 1, 2, 9, 0, 0))
    capsys.readouterr()

    run("backup", "prune", "--keep", "1", "--yes")

    output = capsys.readouterr().out
    assert "Would delete 1 old backup, keeping the newest 1:" in output
    assert "Deleted 1 backup." in output
