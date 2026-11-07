from src.main import main


def run(tmp_path, *argv, db="t.db"):
    return main(["--db", str(tmp_path / db), *argv])


def test_successful_commands_return_zero(tmp_path):
    assert run(tmp_path, "add", "Ship it") == 0
    assert run(tmp_path, "list") == 0
    assert run(tmp_path, "complete", "1") == 0


def test_complete_missing_task_returns_one(tmp_path, capsys):
    assert run(tmp_path, "complete", "9") == 1
    assert "Task not found." in capsys.readouterr().out


def test_corrupt_database_gives_a_friendly_message(tmp_path, capsys):
    (tmp_path / "broken.db").write_text("this is not a database" * 50)

    code = run(tmp_path, "list", db="broken.db")

    captured = capsys.readouterr()
    assert code == 1
    assert "Database error:" in captured.err
    assert "Traceback" not in captured.err


def test_unusable_database_path_gives_a_friendly_message(tmp_path, capsys):
    blocker = tmp_path / "file.txt"
    blocker.write_text("i am a file, not a folder")

    code = main(["--db", str(blocker / "nested" / "t.db"), "list"])

    captured = capsys.readouterr()
    assert code == 1
    assert "error" in captured.err.lower()
    assert "Traceback" not in captured.err


def test_ctrl_c_exits_cleanly(tmp_path, monkeypatch, capsys):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("src.main.filter_tasks", interrupted)
    run(tmp_path, "add", "x")
    capsys.readouterr()

    assert run(tmp_path, "list") == 130
    assert "Cancelled." in capsys.readouterr().out
