import pytest

from src.main import main


def run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "t.db"), *argv]) or 0


def listed(tmp_path, capsys):
    capsys.readouterr()
    run(tmp_path, "list")
    return capsys.readouterr().out


@pytest.fixture
def task(tmp_path, capsys):
    run(tmp_path, "add", "Important task")
    capsys.readouterr()


@pytest.mark.parametrize("answer", ["y", "Y", "yes", " YES "])
def test_delete_proceeds_when_confirmed(tmp_path, task, monkeypatch, capsys, answer):
    monkeypatch.setattr("builtins.input", lambda prompt: answer)

    assert run(tmp_path, "delete", "1") == 0

    assert "Task deleted." in capsys.readouterr().out
    assert "No matching tasks found." in listed(tmp_path, capsys)


@pytest.mark.parametrize("answer", ["", "n", "no", "maybe"])
def test_delete_cancelled_unless_answer_is_yes(tmp_path, task, monkeypatch, capsys, answer):
    monkeypatch.setattr("builtins.input", lambda prompt: answer)

    assert run(tmp_path, "delete", "1") == 0

    assert "Cancelled" in capsys.readouterr().out
    assert "Important task" in listed(tmp_path, capsys)


def test_delete_cancelled_when_there_is_no_input(tmp_path, task, monkeypatch, capsys):
    def no_input(prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", no_input)

    run(tmp_path, "delete", "1")

    assert "Cancelled" in capsys.readouterr().out
    assert "Important task" in listed(tmp_path, capsys)


def test_yes_flag_skips_the_prompt(tmp_path, task, monkeypatch, capsys):
    def fail(prompt):
        raise AssertionError("should not prompt")

    monkeypatch.setattr("builtins.input", fail)

    assert run(tmp_path, "delete", "1", "--yes") == 0
    assert "Task deleted." in capsys.readouterr().out


def test_prompt_names_the_task(tmp_path, task, monkeypatch):
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "n")

    run(tmp_path, "delete", "1")

    assert "Important task" in prompts[0]
    assert "[y/N]" in prompts[0]


def test_delete_missing_task_does_not_prompt(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("prompted"))

    assert run(tmp_path, "delete", "5") == 1
    assert "Task not found." in capsys.readouterr().out
