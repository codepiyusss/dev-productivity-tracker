import pytest

from src.database import Database
from src.main import main


def run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "t.db"), *argv]) or 0


def saved(tmp_path, task_id=1):
    return Database(str(tmp_path / "t.db")).get_task(task_id)


def test_add_with_repeat_saves_the_rule(tmp_path, capsys):
    assert run(tmp_path, "add", "Standup", "--due-date", "2026-12-01", "--repeat", "daily") == 0

    assert saved(tmp_path).recurrence == "daily"


def test_add_repeat_without_due_date_is_rejected(tmp_path, capsys):
    run(tmp_path, "add", "Standup", "--repeat", "daily")

    assert "needs a due date" in capsys.readouterr().out
    assert Database(str(tmp_path / "t.db")).get_all_tasks() == []


def test_add_rejects_unknown_repeat_rule_at_parse_time(tmp_path, capsys):
    with pytest.raises(SystemExit) as exit_info:
        run(tmp_path, "add", "Standup", "--due-date", "2026-12-01", "--repeat", "yearly")

    assert exit_info.value.code == 2
    assert "--repeat" in capsys.readouterr().err


def test_edit_can_set_and_remove_repeat(tmp_path, capsys):
    run(tmp_path, "add", "Standup", "--due-date", "2026-12-01")

    assert run(tmp_path, "edit", "1", "--repeat", "weekly") == 0
    assert saved(tmp_path).recurrence == "weekly"

    assert run(tmp_path, "edit", "1", "--no-repeat") == 0
    assert saved(tmp_path).recurrence is None


def test_edit_repeat_needs_a_due_date(tmp_path, capsys):
    run(tmp_path, "add", "Standup")
    capsys.readouterr()

    assert run(tmp_path, "edit", "1", "--repeat", "daily") == 1
    assert "needs a due date" in capsys.readouterr().out


def test_edit_cannot_clear_due_date_of_a_repeating_task(tmp_path, capsys):
    run(tmp_path, "add", "Standup", "--due-date", "2026-12-01", "--repeat", "daily")
    capsys.readouterr()

    assert run(tmp_path, "edit", "1", "--clear-due-date") == 1
    assert "needs a due date" in capsys.readouterr().out

    assert run(tmp_path, "edit", "1", "--clear-due-date", "--no-repeat") == 0
    task = saved(tmp_path)
    assert (task.due_date, task.recurrence) == (None, None)


def test_repeat_and_no_repeat_are_mutually_exclusive(tmp_path):
    run(tmp_path, "add", "Standup", "--due-date", "2026-12-01")

    with pytest.raises(SystemExit):
        run(tmp_path, "edit", "1", "--repeat", "daily", "--no-repeat")
