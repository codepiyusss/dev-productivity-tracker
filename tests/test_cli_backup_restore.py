import pytest

from src.database import Database
from src.main import main


def titles(path):
    return sorted(t.title for t in Database(str(path)).get_all_tasks())


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "data" / "t.db"), *argv])

    _run("add", "Original")
    _run("backup", "create")
    _run("add", "Added later")
    _run.root = tmp_path
    _run.db = tmp_path / "data" / "t.db"
    _run.backup = next((tmp_path / "data" / "backups").iterdir())
    return _run


def test_restore_with_yes_replaces_the_data(run, capsys):
    capsys.readouterr()

    assert run("backup", "restore", str(run.backup), "--yes") == 0

    output = capsys.readouterr().out
    assert "Backup:  1 tasks" in output
    assert "Current: 2 tasks" in output
    assert "Restored: 1 tasks" in output
    assert "Previous data saved to:" in output
    assert titles(run.db) == ["Original"]


def test_the_previous_data_can_be_recovered_from_the_safety_copy(run, capsys):
    run("backup", "restore", str(run.backup), "--yes")
    safety = [p for p in (run.root / "data" / "backups").iterdir() if "pre-restore" in p.name]

    assert len(safety) == 1
    assert titles(safety[0]) == ["Added later", "Original"]


def test_restore_asks_first_and_cancels_by_default(run, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    capsys.readouterr()

    assert run("backup", "restore", str(run.backup)) == 0

    assert "Cancelled. Nothing was changed." in capsys.readouterr().out
    assert titles(run.db) == ["Added later", "Original"]


def test_restore_proceeds_when_confirmed(run, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")

    assert run("backup", "restore", str(run.backup)) == 0

    assert titles(run.db) == ["Original"]


def test_restore_never_prompts_for_a_bad_file(run, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("prompted"))
    bad = run.root / "bad.db"
    bad.write_text("garbage" * 100)
    capsys.readouterr()

    assert run("backup", "restore", str(bad), "--yes") == 1

    assert "Cannot restore" in capsys.readouterr().out
    assert titles(run.db) == ["Added later", "Original"]


def test_restore_missing_file(run, capsys):
    capsys.readouterr()

    assert run("backup", "restore", str(run.root / "nope.db"), "--yes") == 1

    assert "not found" in capsys.readouterr().out


def test_restore_onto_a_fresh_machine(run, tmp_path, capsys):
    other = tmp_path / "fresh" / "t.db"
    capsys.readouterr()

    code = main(["--db", str(other), "backup", "restore", str(run.backup), "--yes"])

    output = capsys.readouterr().out
    assert code == 0
    assert "Current: empty" in output   # the tool had just created an empty database
    assert "Restored: 1 tasks" in output
    assert titles(other) == ["Original"]
