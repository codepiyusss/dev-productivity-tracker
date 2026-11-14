import pytest

from src.journal import ProductivityJournal
from src.search import search_journal


def entry(date, achievements="", challenges="", next_steps=""):
    return {
        "entry_date": date, "achievements": achievements,
        "challenges": challenges, "next_steps": next_steps,
    }


@pytest.fixture
def entries():
    return [
        entry("2026-11-08", "Shipped the time tracker", "Windows file locking", "Write docs"),
        entry("2026-11-10", "Fixed login bug", "", "Review the tracker backlog"),
        entry("2026-11-09", "Read a book", "Too many meetings", ""),
    ]


def dates(results):
    return [r["entry"]["entry_date"] for r in results]


def test_matches_any_field_and_returns_newest_first(entries):
    assert dates(search_journal(entries, "tracker")) == ["2026-11-10", "2026-11-08"]


def test_reports_the_matching_fields(entries):
    by_date = {r["entry"]["entry_date"]: r for r in search_journal(entries, "tracker")}

    assert by_date["2026-11-08"]["fields"] == ["achievements"]
    assert by_date["2026-11-10"]["fields"] == ["next_steps"]


def test_every_word_must_appear_somewhere_in_the_entry(entries):
    assert dates(search_journal(entries, "tracker locking")) == ["2026-11-08"]
    assert search_journal(entries, "tracker meetings") == []


def test_case_insensitive_substring_matching(entries):
    assert dates(search_journal(entries, "WINDOWS")) == ["2026-11-08"]
    assert dates(search_journal(entries, "lock")) == ["2026-11-08"]


def test_snippet_surrounds_the_first_match():
    long_text = "word " * 20 + "needle" + " word" * 20

    result = search_journal([entry("2026-11-01", long_text)], "needle")[0]

    assert "needle" in result["snippet"]
    assert result["snippet"].startswith("...") and result["snippet"].endswith("...")
    assert len(result["snippet"]) < 80


def test_short_text_is_not_truncated():
    result = search_journal([entry("2026-11-01", "Fixed the bug")], "bug")[0]

    assert result["snippet"] == "Fixed the bug"


def test_snippet_flattens_newlines():
    result = search_journal([entry("2026-11-01", "line one\n\nline two")], "two")[0]

    assert "\n" not in result["snippet"]


def test_missing_fields_and_no_matches_are_handled():
    assert search_journal([{"entry_date": "2026-11-01"}], "anything") == []
    assert search_journal([], "anything") == []


def test_empty_query_is_rejected(entries):
    with pytest.raises(ValueError):
        search_journal(entries, "  ")


def test_works_with_real_journal_entries(tmp_path):
    journal = ProductivityJournal(str(tmp_path / "t.db"))
    journal.add_entry(achievements="Shipped dependencies", entry_date="2026-11-10")
    journal.add_entry(achievements="Wrote tests", entry_date="2026-11-09")

    results = search_journal(journal.get_all_entries(), "dependencies")

    assert dates(results) == ["2026-11-10"]
