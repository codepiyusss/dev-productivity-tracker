from src.main import main


def run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "t.db"), *argv]) or 0


def test_show_prints_every_field(tmp_path, capsys):
    run(tmp_path, "add", "Write docs", "--description", "Cover the CLI",
        "--priority", "high", "--category", "work",
        "--due-date", "2026-12-01", "--tags", "docs,work")
    capsys.readouterr()

    assert run(tmp_path, "show", "1") == 0

    output = capsys.readouterr().out
    assert "Task 1: Write docs" in output
    assert "Status:      Pending" in output
    assert "Priority:    high" in output
    assert "Category:    work" in output
    assert "Due date:    2026-12-01" in output
    assert "Tags:        #docs #work" in output
    assert "Description: Cover the CLI" in output


def test_show_uses_none_for_empty_fields(tmp_path, capsys):
    run(tmp_path, "add", "Bare task")
    capsys.readouterr()

    run(tmp_path, "show", "1")

    output = capsys.readouterr().out
    assert "Due date:    none" in output
    assert "Tags:        none" in output
    assert "Description: none" in output


def test_show_displays_completion_time(tmp_path, capsys):
    run(tmp_path, "add", "Ship it")
    run(tmp_path, "complete", "1")
    capsys.readouterr()

    run(tmp_path, "show", "1")

    assert "Status:      Completed (" in capsys.readouterr().out


def test_show_missing_task(tmp_path, capsys):
    assert run(tmp_path, "show", "42") == 1
    assert "Task not found." in capsys.readouterr().out


def test_reopen_moves_task_back_to_pending(tmp_path, capsys):
    run(tmp_path, "add", "Ship it")
    run(tmp_path, "complete", "1")
    capsys.readouterr()

    assert run(tmp_path, "reopen", "1") == 0
    assert "Task 1 reopened." in capsys.readouterr().out

    run(tmp_path, "show", "1")
    assert "Status:      Pending" in capsys.readouterr().out


def test_reopen_pending_task_is_a_friendly_no_op(tmp_path, capsys):
    run(tmp_path, "add", "Ship it")
    capsys.readouterr()

    assert run(tmp_path, "reopen", "1") == 0
    assert "already pending" in capsys.readouterr().out


def test_reopen_missing_task(tmp_path, capsys):
    assert run(tmp_path, "reopen", "9") == 1
    assert "Task not found." in capsys.readouterr().out
