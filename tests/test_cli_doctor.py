from datetime import datetime

import pytest

from src.backup import create_backup
from src.doctor import CheckResult, format_doctor_report
from src.main import main


def test_format_report_lines_and_summary():
    text = format_doctor_report([
        CheckResult("Database file", "ok", "fine"),
        CheckResult("Backups", "warn", "none yet"),
        CheckResult("Environment", "info", "Python 3"),
    ])

    assert text.splitlines() == [
        "[  OK] Database file: fine",
        "[WARN] Backups: none yet",
        "[INFO] Environment: Python 3",
        "",
        "No problems, but 1 warning(s). 1 check(s) passed.",
    ]


def test_format_report_with_failures_and_all_good():
    failing = format_doctor_report([CheckResult("Database file", "fail", "broken")])
    good = format_doctor_report([CheckResult("Database file", "ok", "fine")])

    assert failing.endswith("1 problem(s) found, 0 warning(s), 0 check(s) passed.")
    assert good.endswith("All good. 1 check(s) passed.")


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "data" / "t.db")
    main(["--db", path, "add", "Write docs"])
    return path


def test_doctor_on_a_healthy_database(db, capsys):
    create_backup(db, now=datetime.now())
    capsys.readouterr()

    assert main(["--db", db, "doctor"]) == 0

    output = capsys.readouterr().out
    assert "[  OK] Database file" in output
    assert "[  OK] Backups" in output
    assert "All good." in output


def test_doctor_warns_but_succeeds_without_backups(db, capsys):
    capsys.readouterr()

    assert main(["--db", db, "doctor"]) == 0

    assert "[WARN] Backups: No backups yet" in capsys.readouterr().out


def test_doctor_works_on_a_corrupt_database_and_exits_with_an_error(tmp_path, capsys):
    bad = tmp_path / "bad.db"
    bad.write_text("garbage" * 300)

    assert main(["--db", str(bad), "doctor"]) == 1

    output = capsys.readouterr().out
    assert "[FAIL] Database file" in output
    assert "Traceback" not in output


def test_doctor_does_not_create_a_missing_database(tmp_path, capsys):
    path = tmp_path / "data" / "nope.db"

    assert main(["--db", str(path), "doctor"]) == 1

    assert "does not exist yet" in capsys.readouterr().out
    assert not path.exists()
