import pytest

from src.database import Database
from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    for title in ("Design", "Build", "Ship"):
        _run("add", title)
    _run.db = str(tmp_path / "t.db")
    return _run


def test_depend_add_links_two_tasks(run, capsys):
    capsys.readouterr()

    assert run("depend", "add", "2", "1") == 0

    assert "Task 2 (Build) now waits for task 1 (Design)." in capsys.readouterr().out
    assert Database(run.db).get_blocker_ids(2) == [1]


def test_depend_add_rejects_unknown_tasks(run, capsys):
    capsys.readouterr()

    assert run("depend", "add", "9", "1") == 1
    assert "Task 9 not found." in capsys.readouterr().out


def test_depend_add_rejects_self_links_and_duplicates(run, capsys):
    run("depend", "add", "2", "1")
    capsys.readouterr()

    assert run("depend", "add", "2", "2") == 1
    assert "cannot depend on itself" in capsys.readouterr().out

    assert run("depend", "add", "2", "1") == 1
    assert "already depends" in capsys.readouterr().out


def test_depend_add_rejects_loops(run, capsys):
    run("depend", "add", "2", "1")
    run("depend", "add", "3", "2")
    capsys.readouterr()

    assert run("depend", "add", "1", "3") == 1

    assert "circular dependency: 1 -> 3 -> 2 -> 1" in capsys.readouterr().out
    assert len(Database(run.db).get_all_dependencies()) == 2


def test_ids_must_be_positive_whole_numbers(run):
    with pytest.raises(SystemExit):
        run("depend", "add", "0", "1")
    with pytest.raises(SystemExit):
        run("depend", "add", "a", "1")


def test_depend_requires_a_subcommand(run):
    with pytest.raises(SystemExit):
        run("depend")
