import csv
import json

import pytest

from src.main import main


@pytest.fixture
def run(tmp_path):
    def _run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    _run("journal", "add", "--date", "2026-11-08", "--achievements", "Early work")
    _run("journal", "add", "--date", "2026-11-10", "--achievements", "Later work")
    _run("journal", "add", "--date", "2026-11-20", "--achievements", "Much later")
    _run.root = tmp_path
    return _run


def test_markdown_is_the_default_format(run, capsys):
    out = run.root / "j.md"
    capsys.readouterr()

    assert run("journal", "export", "--output", str(out)) == 0

    assert "Exported 3 entries to:" in capsys.readouterr().out
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Productivity Journal") and "## 2026-11-20" in text


def test_json_and_csv_formats(run, capsys):
    out_json = run.root / "j.json"
    out_csv = run.root / "j.csv"

    assert run("journal", "export", "--format", "json", "--output", str(out_json)) == 0
    assert run("journal", "export", "--format", "csv", "--output", str(out_csv)) == 0

    assert len(json.loads(out_json.read_text(encoding="utf-8"))) == 3
    with open(out_csv, encoding="utf-8", newline="") as file:
        assert len(list(csv.DictReader(file))) == 3


def test_date_range_limits_the_entries(run, capsys):
    out = run.root / "j.json"
    capsys.readouterr()

    run("journal", "export", "--format", "json", "--output", str(out),
        "--from-date", "2026-11-09", "--to-date", "2026-11-15")

    assert "Exported 1 entry to:" in capsys.readouterr().out
    assert [e["entry_date"] for e in json.loads(out.read_text(encoding="utf-8"))] == ["2026-11-10"]


def test_reversed_date_range_is_rejected(run, capsys):
    capsys.readouterr()

    code = run("journal", "export", "--from-date", "2026-11-20", "--to-date", "2026-11-01",
               "--output", str(run.root / "j.md"))

    assert code == 1
    assert "start date must not be after the end date" in capsys.readouterr().out
    assert not (run.root / "j.md").exists()


def test_default_output_name_uses_the_format(run, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    capsys.readouterr()

    run("journal", "export", "--format", "csv")

    assert (tmp_path / "journal_export.csv").exists()


def test_bad_format_and_bad_dates_are_rejected_at_parse_time(run):
    with pytest.raises(SystemExit):
        run("journal", "export", "--format", "xml")
    with pytest.raises(SystemExit):
        run("journal", "export", "--from-date", "yesterday")


def test_empty_journal_exports_zero_entries(tmp_path, capsys):
    out = tmp_path / "e.md"

    code = main(["--db", str(tmp_path / "empty.db"), "journal", "export", "--output", str(out)])

    assert code == 0
    assert "Exported 0 entries to:" in capsys.readouterr().out
    assert "_No entries._" in out.read_text(encoding="utf-8")


def test_other_journal_commands_still_return_success(run, capsys):
    assert run("journal", "list") == 0
    assert run("journal", "show", "2026-11-08") == 0
