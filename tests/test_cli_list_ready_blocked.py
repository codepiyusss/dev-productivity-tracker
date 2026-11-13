import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    for title in ("Design", "Build", "Ship", "Unrelated"):
        _run("add", title)
    _run("depend", "add", "2", "1")     # Build waits for Design
    _run("depend", "add", "3", "2")     # Ship waits for Build
    return _run


def listed_titles(capsys):
    lines = capsys.readouterr().out.splitlines()
    return sorted(line.split("] ")[1].split(" |")[0] for line in lines if line.startswith("["))


def test_ready_shows_pending_tasks_nothing_blocks(run, capsys):
    capsys.readouterr()

    run("list", "--ready")

    assert listed_titles(capsys) == ["Design", "Unrelated"]


def test_blocked_shows_tasks_waiting_on_unfinished_tasks(run, capsys):
    capsys.readouterr()

    run("list", "--blocked")

    assert listed_titles(capsys) == ["Build", "Ship"]


def test_completing_a_blocker_moves_tasks_between_the_lists(run, capsys):
    run("complete", "1")
    capsys.readouterr()

    run("list", "--ready")
    assert listed_titles(capsys) == ["Build", "Unrelated"]

    run("list", "--blocked")
    assert listed_titles(capsys) == ["Ship"]


def test_completed_tasks_never_appear_in_either_list(run, capsys):
    run("complete", "4")
    capsys.readouterr()

    run("list", "--ready")

    assert "Unrelated" not in listed_titles(capsys)


def test_filters_combine_with_other_options(run, capsys):
    run("add", "Urgent ready task", "--priority", "high")
    capsys.readouterr()

    run("list", "--ready", "--priority", "high")

    assert listed_titles(capsys) == ["Urgent ready task"]


def test_empty_result_message(run, capsys):
    run("complete", "1")
    run("complete", "2")
    capsys.readouterr()

    run("list", "--blocked")

    assert "No matching tasks found." in capsys.readouterr().out


def test_ready_and_blocked_cannot_be_combined(run):
    with pytest.raises(SystemExit):
        run("list", "--ready", "--blocked")


def test_plain_list_is_unchanged(run, capsys):
    capsys.readouterr()

    run("list")

    assert len(listed_titles(capsys)) == 4
