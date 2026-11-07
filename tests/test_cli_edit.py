from src.main import main


def run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "t.db"), *argv]) or 0


def add_task(tmp_path, capsys):
    run(tmp_path, "add", "Write docs", "--priority", "low",
        "--category", "work", "--due-date", "2026-12-01")
    capsys.readouterr()


def test_edit_changes_only_the_given_fields(tmp_path, capsys):
    add_task(tmp_path, capsys)

    code = run(tmp_path, "edit", "1", "--title", "Write better docs",
               "--priority", "high")

    output = capsys.readouterr().out
    assert code == 0
    assert "Task 1 updated." in output
    assert "Write better docs | high | work" in output

    run(tmp_path, "list")
    assert "Write better docs" in capsys.readouterr().out


def test_edit_can_set_and_clear_due_date(tmp_path, capsys):
    add_task(tmp_path, capsys)

    assert run(tmp_path, "edit", "1", "--due-date", "2999-01-15") == 0
    capsys.readouterr()
    run(tmp_path, "reminders", "--days", "999999")
    assert "Write docs" in capsys.readouterr().out

    assert run(tmp_path, "edit", "1", "--clear-due-date") == 0
    capsys.readouterr()
    run(tmp_path, "reminders", "--days", "999999")
    assert "Write docs" not in capsys.readouterr().out


def test_edit_without_fields_explains_what_to_do(tmp_path, capsys):
    add_task(tmp_path, capsys)

    assert run(tmp_path, "edit", "1") == 1
    assert "Nothing to change" in capsys.readouterr().out


def test_edit_missing_task_returns_error_code(tmp_path, capsys):
    assert run(tmp_path, "edit", "99", "--title", "x") == 1
    assert "Task not found." in capsys.readouterr().out


def test_edit_rejects_invalid_values_without_changing_the_task(tmp_path, capsys):
    add_task(tmp_path, capsys)

    assert run(tmp_path, "edit", "1", "--title", "   ") == 1
    assert "title cannot be empty" in capsys.readouterr().out
    assert run(tmp_path, "edit", "1", "--category", " ") == 1
    assert "Category cannot be empty." in capsys.readouterr().out

    run(tmp_path, "list")
    assert "Write docs | low | work" in capsys.readouterr().out


def test_edit_due_date_options_are_mutually_exclusive(tmp_path, capsys):
    add_task(tmp_path, capsys)

    import pytest
    with pytest.raises(SystemExit):
        run(tmp_path, "edit", "1", "--due-date", "2027-01-01", "--clear-due-date")


def test_edit_keeps_tags(tmp_path, capsys):
    run(tmp_path, "add", "Tagged", "--tags", "work,urgent")
    capsys.readouterr()

    run(tmp_path, "edit", "1", "--priority", "high")

    assert "#work #urgent" in capsys.readouterr().out
