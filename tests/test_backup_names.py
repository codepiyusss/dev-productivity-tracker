from datetime import datetime

import pytest

from src.backup import backup_filename, clean_label, parse_backup_name

NOW = datetime(2026, 11, 10, 15, 30, 5)


def test_filename_without_label():
    assert backup_filename(NOW) == "productivity-20261110-153005.db"


def test_filename_with_label():
    assert backup_filename(NOW, "before import") == (
        "productivity-20261110-153005-before-import.db"
    )


def test_filename_defaults_to_the_current_time():
    assert parse_backup_name(backup_filename()) is not None


@pytest.mark.parametrize("label, expected", [
    ("Before Import", "before-import"),
    ("  weekly!!  ", "weekly"),
    ("a/b\\c", "a-b-c"),
    ("../../etc/passwd", "etc-passwd"),
    ("x" * 50, "x" * 30),
    ("---", None),
    ("", None),
    (None, None),
    ("ünïcode", "n-code"),
])
def test_clean_label(label, expected):
    assert clean_label(label) == expected


def test_labels_cannot_escape_the_backup_folder():
    name = backup_filename(NOW, "../../evil")

    assert "/" not in name and "\\" not in name and ".." not in name


def test_parse_round_trip():
    created, label = parse_backup_name(backup_filename(NOW, "Nightly"))

    assert created == NOW
    assert label == "nightly"


def test_parse_name_without_label():
    assert parse_backup_name("productivity-20261110-153005.db") == (NOW, None)


@pytest.mark.parametrize("name", [
    "productivity.db", "notes.txt", "productivity-2026-11-10.db",
    "productivity-20261310-153005.db",  # month 13
    "productivity-20261110-153005.db.tmp",
    "backup-20261110-153005.db",
    "productivity-20261110-153005-UPPER.db",
])
def test_parse_rejects_foreign_files(name):
    assert parse_backup_name(name) is None
