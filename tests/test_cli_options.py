import pytest

from src.main import build_parser, main


def run(tmp_path, *argv, db="cli.db"):
    return main(["--db", str(tmp_path / db), *argv])


def test_db_option_uses_the_given_database_file(tmp_path, capsys):
    run(tmp_path, "add", "Write docs")
    capsys.readouterr()

    run(tmp_path, "list")
    assert "Write docs" in capsys.readouterr().out

    # A different database file starts empty.
    run(tmp_path, "list", db="other.db")
    assert "No matching tasks found." in capsys.readouterr().out
    assert (tmp_path / "cli.db").exists()
    assert (tmp_path / "other.db").exists()


def test_db_option_is_also_used_by_the_journal(tmp_path, capsys):
    run(tmp_path, "journal", "add", "--achievements", "Shipped it", "--date", "2026-11-10")
    capsys.readouterr()

    run(tmp_path, "journal", "show", "2026-11-10")
    assert "Shipped it" in capsys.readouterr().out

    run(tmp_path, "journal", "show", "2026-11-10", db="other.db")
    assert "not found" in capsys.readouterr().out.lower()


def test_main_returns_without_error_for_normal_commands(tmp_path):
    assert (run(tmp_path, "stats") or 0) == 0


def test_help_shows_examples_and_db_option(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    output = capsys.readouterr().out
    assert exit_info.value.code == 0
    assert "--db PATH" in output
    assert "examples:" in output
    assert "python -m src.main goal set daily 3" in output


def test_parser_still_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
