from datetime import date

from src.main import format_task_details, format_task_line, main
from src.models.task import Task

TODAY = date(2026, 11, 10)


def task(**kwargs):
    return Task("Standup", task_id=2, created_at="2026-11-10T09:00:00", **kwargs)


def test_listing_shows_the_repeat_rule_after_the_due_date():
    line = format_task_line(task(due_date="2026-12-01", recurrence="weekly"), TODAY)

    assert line == (
        "[2] Standup | medium | general | Pending | due 2026-12-01 | repeats weekly"
    )


def test_listing_puts_tags_after_the_repeat_rule():
    line = format_task_line(
        task(due_date="2026-12-01", recurrence="daily", tags=["team"]), TODAY
    )

    assert line.endswith("| repeats daily | #team")


def test_overdue_marker_comes_before_the_repeat_rule():
    line = format_task_line(task(due_date="2026-11-01", recurrence="daily"), TODAY)

    assert line.endswith("| due 2026-11-01 (OVERDUE) | repeats daily")


def test_plain_listing_is_unchanged():
    assert "repeats" not in format_task_line(task(due_date="2026-12-01"), TODAY)


def test_details_show_the_repeat_rule():
    assert "  Repeats:     weekly" in format_task_details(
        task(due_date="2026-12-01", recurrence="weekly")
    )
    assert "  Repeats:     no" in format_task_details(task())


def test_time_spent_still_sits_just_before_the_description():
    lines = format_task_details(
        task(due_date="2026-12-01", recurrence="daily"), tracked_seconds=600
    ).splitlines()

    assert lines[-2] == "  Time spent:  10m"
    assert lines[-1].startswith("  Description:")
    assert lines.index("  Repeats:     daily") < lines.index("  Time spent:  10m")


def test_show_and_list_commands_include_the_rule(tmp_path, capsys):
    def run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    run("add", "Standup", "--due-date", "2999-01-01", "--repeat", "monthly")
    capsys.readouterr()

    run("list")
    assert "repeats monthly" in capsys.readouterr().out

    run("show", "1")
    assert "Repeats:     monthly" in capsys.readouterr().out
