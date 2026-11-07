import argparse

import pytest

from src.main import main, non_negative_int, positive_int, valid_date


def run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "t.db"), *argv])


def test_positive_int_accepts_and_rejects():
    assert positive_int("5") == 5

    for bad in ("0", "-3", "abc", "2.5"):
        with pytest.raises(argparse.ArgumentTypeError):
            positive_int(bad)


def test_non_negative_int_accepts_zero():
    assert non_negative_int("0") == 0

    with pytest.raises(argparse.ArgumentTypeError, match="negative"):
        non_negative_int("-1")


def test_valid_date_normalizes_and_rejects():
    assert valid_date("2026-1-5") == "2026-01-05"

    for bad in ("31-12-2026", "2026-02-30", "soon"):
        with pytest.raises(argparse.ArgumentTypeError, match="YYYY-MM-DD"):
            valid_date(bad)


@pytest.mark.parametrize("argv", [
    ["add", "x", "--due-date", "31-12-2026"],
    ["complete", "0"],
    ["complete", "-4"],
    ["delete", "abc"],
    ["tag", "add", "0", "work"],
    ["journal", "show", "banana"],
    ["journal", "list", "--limit", "0"],
    ["journal", "list", "--from-date", "13/11/2026"],
    ["reminders", "--days", "-2"],
])
def test_invalid_arguments_are_rejected_before_anything_runs(tmp_path, argv, capsys):
    with pytest.raises(SystemExit) as exit_info:
        run(tmp_path, *argv)

    assert exit_info.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_error_message_names_the_problem(tmp_path, capsys):
    with pytest.raises(SystemExit):
        run(tmp_path, "add", "x", "--due-date", "31-12-2026")

    err = capsys.readouterr().err
    assert "--due-date" in err
    assert "use YYYY-MM-DD" in err


def test_valid_arguments_still_work(tmp_path, capsys):
    run(tmp_path, "add", "Ship it", "--due-date", "2026-1-5")
    run(tmp_path, "journal", "add", "--date", "2026-11-10", "--achievements", "ok")
    run(tmp_path, "reminders", "--days", "0")
    capsys.readouterr()

    run(tmp_path, "list")
    assert "Ship it" in capsys.readouterr().out
