import pytest

from src.database import Database
from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    _run("add", "A", "--tags", "bug,urgent")
    _run("add", "B", "--tags", "bug")
    _run("add", "C", "--tags", "fix")
    _run.db = str(tmp_path / "t.db")
    return _run


def counts(run):
    return Database(run.db).get_tag_counts()


def test_rename(run, capsys):
    capsys.readouterr()

    assert run("tag", "rename", "bug", "defect") == 0

    assert "Renamed #bug to #defect on 2 tasks." in capsys.readouterr().out
    assert counts(run) == {"defect": 2, "fix": 1, "urgent": 1}


def test_rename_singular_wording_and_normalization(run, capsys):
    capsys.readouterr()

    run("tag", "rename", "#FIX", "repair")

    assert "Renamed #fix to #repair on 1 task." in capsys.readouterr().out


def test_rename_to_existing_tag_is_refused(run, capsys):
    capsys.readouterr()

    assert run("tag", "rename", "bug", "fix") == 1

    assert "already exists. Use merge" in capsys.readouterr().out
    assert counts(run)["bug"] == 2


def test_merge(run, capsys):
    capsys.readouterr()

    assert run("tag", "merge", "fix", "bug") == 0

    assert "Merged #fix into #bug (1 task)." in capsys.readouterr().out
    assert counts(run) == {"bug": 3, "urgent": 1}


def test_merge_errors(run, capsys):
    capsys.readouterr()

    assert run("tag", "merge", "bug", "bug") == 1
    assert "two different tags" in capsys.readouterr().out
    assert run("tag", "merge", "ghost", "bug") == 1
    assert "'ghost' not found" in capsys.readouterr().out


def test_delete_with_yes(run, capsys):
    capsys.readouterr()

    assert run("tag", "delete", "bug", "--yes") == 0

    assert "Removed #bug from 2 tasks." in capsys.readouterr().out
    assert "bug" not in counts(run)


def test_delete_asks_first_and_cancels_by_default(run, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    capsys.readouterr()

    assert run("tag", "delete", "bug") == 0

    assert "Cancelled. Nothing was changed." in capsys.readouterr().out
    assert counts(run)["bug"] == 2


def test_delete_proceeds_when_confirmed_and_unknown_tag_never_prompts(run, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    assert run("tag", "delete", "fix") == 0

    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("prompted"))
    capsys.readouterr()
    assert run("tag", "delete", "ghost") == 1
    assert "'ghost' not found" in capsys.readouterr().out


def test_existing_tag_commands_still_work_and_report_failures(run, capsys):
    assert run("tag", "add", "3", "extra") == 0
    assert run("tag", "remove", "3", "extra") == 0
    assert run("tag", "list") == 0
    assert run("tag", "add", "99", "x") == 1
    capsys.readouterr()
    run("tag", "add", "99", "x")
    assert "Task not found." in capsys.readouterr().out
