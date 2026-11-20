import csv
import json

import pytest

from src.journal import ProductivityJournal
from src.journal_export import (
    FIELDS, export_journal, export_journal_csv, export_journal_json, export_journal_markdown,
)


@pytest.fixture
def entries(tmp_path):
    journal = ProductivityJournal(str(tmp_path / "t.db"))
    journal.add_entry(achievements="Shipped, tested", challenges="Edge \"cases\"",
                      next_steps="Write docs\nsecond line", entry_date="2026-11-10")
    journal.add_entry(achievements="Café ☕ planning", entry_date="2026-11-08")
    return journal.get_all_entries()


def read(path):
    return open(path, encoding="utf-8").read()


def test_json_export_is_oldest_first_with_all_fields(entries, tmp_path):
    path = export_journal_json(entries, str(tmp_path / "j.json"))

    data = json.loads(read(path))

    assert [d["entry_date"] for d in data] == ["2026-11-08", "2026-11-10"]
    assert set(data[0]) == set(FIELDS)
    assert data[1]["challenges"] == 'Edge "cases"'
    assert "Café ☕ planning" in read(path)


def test_csv_export_escapes_commas_quotes_and_newlines(entries, tmp_path):
    path = export_journal_csv(entries, str(tmp_path / "j.csv"))

    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert reader.fieldnames == FIELDS
    assert [r["entry_date"] for r in rows] == ["2026-11-08", "2026-11-10"]
    assert rows[1]["achievements"] == "Shipped, tested"
    assert rows[1]["next_steps"] == "Write docs\nsecond line"
    assert rows[0]["challenges"] == ""


def test_markdown_export_layout(entries, tmp_path):
    text = read(export_journal_markdown(entries, str(tmp_path / "j.md")))

    assert text.startswith("# Productivity Journal\n\n## 2026-11-08\n")
    assert text.index("## 2026-11-08") < text.index("## 2026-11-10")
    assert "**Achievements**\n\nShipped, tested" in text
    assert "**Next steps**\n\nWrite docs\nsecond line" in text
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_markdown_omits_empty_sections(entries, tmp_path):
    text = read(export_journal_markdown(entries, str(tmp_path / "j.md")))
    first_entry = text.split("## 2026-11-10")[0]

    assert "**Achievements**" in first_entry
    assert "**Challenges**" not in first_entry and "**Next steps**" not in first_entry


def test_empty_journal_exports_cleanly(tmp_path):
    assert read(export_journal_markdown([], str(tmp_path / "e.md"))) == (
        "# Productivity Journal\n\n_No entries._\n"
    )
    assert json.loads(read(export_journal_json([], str(tmp_path / "e.json")))) == []
    assert read(export_journal_csv([], str(tmp_path / "e.csv"))).strip() == ",".join(FIELDS)


def test_export_creates_missing_folders(entries, tmp_path):
    path = export_journal(entries, str(tmp_path / "a" / "b" / "j.json"), "json")

    assert json.loads(read(path))


def test_dispatcher_is_case_insensitive_and_rejects_unknown_formats(entries, tmp_path):
    assert read(export_journal(entries, str(tmp_path / "j.md"), "MD")).startswith("# Productivity")

    with pytest.raises(ValueError, match="Choose from: md, json, csv"):
        export_journal(entries, str(tmp_path / "j.xml"), "xml")
