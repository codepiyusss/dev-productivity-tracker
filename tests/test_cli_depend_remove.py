import pytest

from src.database import Database
from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    for title in ("Design", "Build", "Ship"):
        _run("add", title)
    _run("depend", "add", "2", "1")
    _run("depend", "add", "3", "2")
    _run.db = str(tmp_path / "t.db")
    return _run


def test_depend_remove_deletes_the_link(run, capsys):
    capsys.readouterr()

    assert run("depend", "remove", "2", "1") == 0

    assert "Task 2 no longer waits for task 1." in capsys.readouterr().out
    assert Database(run.db).get_all_dependencies() == [(3, 2)]


def test_depend_remove_unknown_link_fails(run, capsys):
    capsys.readouterr()

    assert run("depend", "remove", "1", "2") == 1

    assert "Task 1 does not depend on task 2." in capsys.readouterr().out
    assert len(Database(run.db).get_all_dependencies()) == 2


def test_removed_link_can_be_added_back(run, capsys):
    run("depend", "remove", "2", "1")
    capsys.readouterr()

    assert run("depend", "add", "2", "1") == 0


def test_remove_validates_ids(run):
    with pytest.raises(SystemExit):
        run("depend", "remove", "0", "1")
