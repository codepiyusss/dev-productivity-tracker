import json

import pytest

from src.database import Database
from src.main import detect_import_format, main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    _run.root = tmp_path
    _run.db = str(tmp_path / "t.db")
    return _run


def titles(run):
    return sorted(t.title for t in Database(run.db).get_all_tasks())


@pytest.mark.parametrize("name, explicit, expected", [
    ("tasks.json", None, "json"), ("TASKS.JSON", None, "json"),
    ("tasks.csv", None, "csv"), ("tasks.txt", None, "csv"), ("tasks", None, "csv"),
    ("tasks.csv", "json", "json"), ("tasks.json", "csv", "csv"),
])
def test_detect_import_format(name, explicit, expected):
    assert detect_import_format(name, explicit) == expected


def test_json_file_is_detected_by_extension(run, capsys):
    path = run.root / "in.json"
    path.write_text(json.dumps([{"title": "A"}, {"title": "B", "tags": ["x"]}]), encoding="utf-8")
    capsys.readouterr()

    assert run("import", str(path)) == 0

    assert "Imported 2 tasks." in capsys.readouterr().out
    assert titles(run) == ["A", "B"]


def test_format_option_overrides_the_extension(run, capsys):
    path = run.root / "tasks.dat"
    path.write_text(json.dumps([{"title": "From dat"}]), encoding="utf-8")

    assert run("import", str(path), "--format", "json") == 0

    assert titles(run) == ["From dat"]


def test_csv_import_is_unchanged(run, capsys):
    path = run.root / "in.csv"
    path.write_text("title\nCsv task\n", encoding="utf-8")

    assert run("import", str(path)) == 0

    assert titles(run) == ["Csv task"]


def test_json_dry_run_and_backup_options_work(run, capsys):
    run("add", "Existing")
    path = run.root / "in.json"
    path.write_text(json.dumps([{"title": "New"}]), encoding="utf-8")
    capsys.readouterr()

    run("import", str(path), "--dry-run")
    assert "[Dry run] Would import 1 task." in capsys.readouterr().out
    assert titles(run) == ["Existing"]

    run("import", str(path), "--backup")
    assert "Backup saved before import:" in capsys.readouterr().out
    assert titles(run) == ["Existing", "New"]


def test_json_errors_are_reported_cleanly(run, capsys):
    bad = run.root / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    capsys.readouterr()

    assert run("import", str(bad)) == 1
    assert "Could not import tasks: Invalid JSON at line 1" in capsys.readouterr().out

    partly = run.root / "partly.json"
    partly.write_text(json.dumps([{"title": "Fine"}, "oops"]), encoding="utf-8")
    assert run("import", str(partly)) == 0
    output = capsys.readouterr().out
    assert "Imported 1 task." in output
    assert "Item 2: expected an object, not str" in output


def test_export_json_then_import_json_through_the_cli(run, capsys):
    run("add", "Write docs", "--tags", "docs", "--priority", "high")
    run("export", "--format", "json", "--output", str(run.root / "out.json"))
    capsys.readouterr()

    code = main(["--db", str(run.root / "other.db"), "import", str(run.root / "out.json")])

    assert code == 0
    other = Database(str(run.root / "other.db")).get_all_tasks()[0]
    assert (other.title, other.priority, other.tags) == ("Write docs", "high", ["docs"])
