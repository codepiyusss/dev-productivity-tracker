from datetime import date, timedelta

import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    today = date.today()
    _run("add", "Late task", "--due-date", (today - timedelta(days=3)).isoformat())
    _run("add", "Today task", "--due-date", today.isoformat())
    _run("add", "Soon task", "--due-date", (today + timedelta(days=2)).isoformat())
    _run("add", "Far task", "--due-date", (today + timedelta(days=40)).isoformat())
    _run("add", "Undated task")
    _run("add", "Finished late", "--due-date", (today - timedelta(days=9)).isoformat())
    _run("complete", "6")
    return _run


def listed(capsys):
    lines = capsys.readouterr().out.splitlines()
    return sorted(line.split("] ")[1].split(" |")[0] for line in lines if line.startswith("["))


def test_overdue(run, capsys):
    capsys.readouterr()
    run("list", "--overdue")
    assert listed(capsys) == ["Late task"]


def test_due_today(run, capsys):
    capsys.readouterr()
    run("list", "--due-today")
    assert listed(capsys) == ["Today task"]


def test_due_within_days(run, capsys):
    capsys.readouterr()
    run("list", "--due-within", "3")
    assert listed(capsys) == ["Soon task", "Today task"]

    run("list", "--due-within", "0")
    assert listed(capsys) == ["Today task"]


def test_no_due_date(run, capsys):
    capsys.readouterr()
    run("list", "--no-due-date")
    assert listed(capsys) == ["Undated task"]


def test_filters_combine_with_other_options(run, capsys):
    run("add", "Urgent today", "--due-date", date.today().isoformat(), "--priority", "high")
    capsys.readouterr()

    run("list", "--due-today", "--priority", "high")

    assert listed(capsys) == ["Urgent today"]


def test_filters_combine_with_ready_and_blocked(run, capsys):
    run("depend", "add", "2", "1")       # Today task waits for Late task
    capsys.readouterr()

    run("list", "--due-today", "--blocked")
    assert listed(capsys) == ["Today task"]

    run("list", "--due-today", "--ready")
    assert capsys.readouterr().out.strip() == "No matching tasks found."


def test_empty_result(run, capsys):
    run("complete", "1")
    capsys.readouterr()

    run("list", "--overdue")

    assert "No matching tasks found." in capsys.readouterr().out


def test_due_filters_are_mutually_exclusive_and_validated(run):
    with pytest.raises(SystemExit):
        run("list", "--overdue", "--due-today")
    with pytest.raises(SystemExit):
        run("list", "--due-within", "-1")
    with pytest.raises(SystemExit):
        run("list", "--due-within", "abc")


def test_plain_list_is_unchanged(run, capsys):
    capsys.readouterr()
    run("list")
    assert len(listed(capsys)) == 6
