import pytest

from src.backup import list_backups
from src.database import Database
from src.main import main
from src.models.task import Task


@pytest.fixture
def run(tmp_path):
    db = str(tmp_path / "data" / "t.db")

    def _run(*argv):
        return main(["--db", db, *argv])

    _run("add", "Recent")
    database = Database(db)
    database.add_task(Task("Ancient A", completed=True, completed_at="2020-01-01T09:00:00"))
    database.add_task(Task("Ancient B", completed=True, completed_at="2020-02-01T09:00:00"))
    database.add_task(Task("Legacy", completed=True))
    _run.db = db
    _run.folder = tmp_path / "data" / "backups"
    return _run


def titles(run):
    return sorted(t.title for t in Database(run.db).get_all_tasks())


def test_dry_run_lists_tasks_and_deletes_nothing(run, capsys):
    capsys.readouterr()

    assert run("purge", "--older-than", "30", "--dry-run") == 0

    output = capsys.readouterr().out
    assert "2 completed task(s) finished 30+ days ago would be deleted:" in output
    assert "Ancient A (completed 2020-01-01)" in output
    assert "Dry run: nothing was deleted." in output
    assert len(titles(run)) == 4
    assert not run.folder.exists()


def test_purge_with_yes_backs_up_then_deletes(run, capsys):
    capsys.readouterr()

    assert run("purge", "--older-than", "30", "--yes") == 0

    output = capsys.readouterr().out
    assert "Backup saved:" in output and "Deleted 2 task(s)." in output
    assert titles(run) == ["Legacy", "Recent"]
    backup = list_backups(run.folder)[0]
    assert backup["label"] == "before-purge" and backup["counts"]["tasks"] == 4


def test_the_backup_can_undo_a_purge(run):
    run("purge", "--older-than", "30", "--yes")
    backup = list_backups(run.folder)[0]["path"]

    run("backup", "restore", backup, "--yes")

    assert len(titles(run)) == 4


def test_purge_asks_first_and_cancels_by_default(run, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    capsys.readouterr()

    assert run("purge", "--older-than", "30") == 0

    assert "Cancelled. Nothing was deleted." in capsys.readouterr().out
    assert len(titles(run)) == 4 and not run.folder.exists()


def test_purge_proceeds_when_confirmed(run, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    run("purge", "--older-than", "30")

    assert titles(run) == ["Legacy", "Recent"]


def test_include_undated_also_removes_legacy_completions(run, capsys):
    capsys.readouterr()

    run("purge", "--older-than", "30", "--include-undated", "--yes")

    assert titles(run) == ["Recent"]
    assert "[4] Legacy (completed unknown date)" in capsys.readouterr().out


def test_no_backup_skips_the_backup(run):
    run("purge", "--older-than", "30", "--yes", "--no-backup")

    assert titles(run) == ["Legacy", "Recent"]
    assert not run.folder.exists()


def test_nothing_to_purge(run, capsys):
    capsys.readouterr()

    assert run("purge", "--older-than", "100000") == 0

    assert "Nothing to purge" in capsys.readouterr().out


def test_backup_failure_stops_the_purge(run, capsys, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("disk full")

    monkeypatch.setattr("src.main.create_backup", broken)
    capsys.readouterr()

    assert run("purge", "--older-than", "30", "--yes") == 1

    assert "Backup failed, so nothing was deleted: disk full" in capsys.readouterr().out
    assert len(titles(run)) == 4


def test_older_than_is_required_and_must_be_positive(run):
    with pytest.raises(SystemExit):
        run("purge")
    with pytest.raises(SystemExit):
        run("purge", "--older-than", "0")
