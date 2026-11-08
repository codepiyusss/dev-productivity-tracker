import json
from datetime import date, datetime

import pytest

from src.database import Database
from src.main import main
from src.models.task import Task
from src.timetracking import TimeTracker, format_time_summary

NOW = datetime(2026, 11, 10, 18, 0, 0)


@pytest.fixture
def summary():
    database = Database(":memory:")
    database.add_task(Task("Write docs", category="work"))
    database.add_task(Task("Read book", category="home"))
    tracker = TimeTracker(database)
    tracker.log_manual(1, 5400, day=date(2026, 11, 10), now=NOW)
    tracker.log_manual(2, 1800, day=date(2026, 11, 9), now=NOW)
    return tracker.get_summary(days=3, now=NOW)


def test_summary_text_sections(summary):
    text = format_time_summary(summary)

    assert text.splitlines()[0] == (
        "Time tracked in the last 3 day(s): 2h (2 entries)"
    )
    assert "  2026-11-08  -" in text
    assert "  2026-11-09  30m" in text
    assert "  2026-11-10  1h 30m" in text
    assert "  work: 1h 30m" in text
    assert "  [1] Write docs: 1h 30m" in text


def test_empty_summary_is_a_single_line():
    database = Database(":memory:")
    summary = TimeTracker(database).get_summary(days=7, now=NOW)

    assert format_time_summary(summary) == (
        "Time tracked in the last 7 day(s): 0s (0 entries)"
    )


def test_singular_entry_wording():
    database = Database(":memory:")
    database.add_task(Task("Solo"))
    tracker = TimeTracker(database)
    tracker.log_manual(1, 600, now=NOW)

    assert "(1 entry)" in format_time_summary(tracker.get_summary(days=1, now=NOW))


def test_top_tasks_limit(summary):
    text = format_time_summary(summary, top_tasks=1)

    assert "Write docs" in text
    assert "Read book" not in text


def test_cli_summary_text_and_json(tmp_path, capsys):
    def run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    run("add", "Write docs", "--category", "work")
    run("timer", "log", "1", "1h")
    capsys.readouterr()

    assert run("timer", "summary", "--days", "2") == 0
    assert "Time tracked in the last 2 day(s): 1h (1 entry)" in capsys.readouterr().out

    run("timer", "summary", "--json")
    data = json.loads(capsys.readouterr().out)
    assert data["total_seconds"] == 3600
    assert data["by_category"][0]["category"] == "work"
