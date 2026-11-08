import pytest

from src.database import Database
from src.main import main
from src.models.task import Task


def test_get_time_entry():
    database = Database(":memory:")
    database.add_task(Task("A"))
    entry = database.add_time_entry(1, "2026-11-10T09:00:00", "2026-11-10T10:00:00")

    assert database.get_time_entry(entry["entry_id"]) == entry
    assert database.get_time_entry(99) is None


@pytest.fixture
def run(tmp_path, capsys):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    _run("add", "Write docs")
    _run("timer", "log", "1", "30m")
    capsys.readouterr()
    return _run


def entries(capsys, run):
    run("timer", "list")
    return capsys.readouterr().out


def test_delete_with_yes_removes_the_entry(run, capsys):
    assert run("timer", "delete", "1", "--yes") == 0
    assert "Time entry 1 deleted." in capsys.readouterr().out
    assert "No time entries" in entries(capsys, run)


def test_delete_asks_first_and_cancels_by_default(run, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    assert run("timer", "delete", "1") == 0

    assert "Cancelled" in capsys.readouterr().out
    assert "30m" in entries(capsys, run)


def test_delete_proceeds_when_confirmed(run, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    assert run("timer", "delete", "1") == 0
    assert "deleted" in capsys.readouterr().out


def test_delete_unknown_entry(run, capsys):
    assert run("timer", "delete", "42", "--yes") == 1
    assert "Time entry 42 not found." in capsys.readouterr().out


def test_deleting_a_running_entry_lets_a_new_timer_start(run, capsys):
    run("timer", "start", "1")
    capsys.readouterr()
    run("timer", "list")
    running_id = [
        line for line in capsys.readouterr().out.splitlines() if "(running)" in line
    ][0].split()[0].lstrip("#")

    assert run("timer", "delete", running_id, "--yes") == 0
    assert run("timer", "start", "1") == 0
