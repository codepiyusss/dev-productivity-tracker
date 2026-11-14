import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    _run("add", "Write Python docs", "--tags", "docs", "--category", "work")
    _run("add", "Fix login bug", "--description", "python traceback")
    _run("add", "Buy milk")
    _run("journal", "add", "--achievements", "Learned python typing", "--date", "2026-11-10")
    _run("journal", "add", "--achievements", "Went for a run", "--date", "2026-11-09")
    return _run


def test_search_finds_tasks_and_journal_entries(run, capsys):
    capsys.readouterr()

    assert run("search", "python") == 0

    output = capsys.readouterr().out
    assert "Tasks (2):" in output
    assert "Write Python docs" in output and "Fix login bug" in output
    assert "(matched: title)" in output and "(matched: description)" in output
    assert "Journal (1):" in output
    assert "2026-11-10  Learned python typing  (achievements)" in output


def test_best_match_comes_first(run, capsys):
    capsys.readouterr()

    run("search", "python")

    output = capsys.readouterr().out
    assert output.index("Write Python docs") < output.index("Fix login bug")


def test_multiple_words_must_all_match(run, capsys):
    capsys.readouterr()

    run("search", "python", "traceback")

    output = capsys.readouterr().out
    assert "Fix login bug" in output and "Write Python docs" not in output


def test_tasks_only_and_journal_only(run, capsys):
    capsys.readouterr()
    run("search", "python", "--tasks")
    tasks_only = capsys.readouterr().out
    run("search", "python", "--journal")
    journal_only = capsys.readouterr().out

    assert "Tasks (2):" in tasks_only and "Journal" not in tasks_only
    assert "Journal (1):" in journal_only and "Tasks" not in journal_only


def test_no_matches(run, capsys):
    capsys.readouterr()

    assert run("search", "zebra") == 0

    assert 'No matches for "zebra".' in capsys.readouterr().out


def test_limit_truncates_each_section(run, capsys):
    capsys.readouterr()

    run("search", "python", "--limit", "1")

    output = capsys.readouterr().out
    assert "Tasks (2):" in output and "...and 1 more." in output
    assert "Fix login bug" not in output


def test_blank_query_is_rejected(run, capsys):
    capsys.readouterr()

    assert run("search", " ") == 1
    assert "something to search for" in capsys.readouterr().out


def test_search_needs_a_query_and_a_positive_limit(run):
    with pytest.raises(SystemExit):
        run("search")
    with pytest.raises(SystemExit):
        run("search", "x", "--limit", "0")
    with pytest.raises(SystemExit):
        run("search", "x", "--tasks", "--journal")


def test_search_does_not_change_anything(run, capsys):
    run("search", "python")
    capsys.readouterr()

    run("list")

    assert capsys.readouterr().out.count("[") == 3
