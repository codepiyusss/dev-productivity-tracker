import json
from argparse import Namespace

from src.database import Database
from src.main import handle_streak
from src.tasks import TaskManager


def manager_with_completion():
    manager = TaskManager(Database(":memory:"))
    task = manager.create_task("Ship it")
    manager.complete_task(task.task_id)
    return manager


def test_streak_command_prints_summary(capsys):
    handle_streak(manager_with_completion(), Namespace(days=7, json=False))

    output = capsys.readouterr().out
    assert "Current streak: 1 day (completed a task today)" in output
    assert "Last 7 days: [------#]" in output


def test_streak_command_json_output(capsys):
    handle_streak(manager_with_completion(), Namespace(days=3, json=True))

    data = json.loads(capsys.readouterr().out)
    assert data["current"] == 1
    assert len(data["recent"]) == 3


def test_streak_command_with_no_history(capsys):
    handle_streak(TaskManager(Database(":memory:")), Namespace(days=5, json=False))

    assert "Current streak: 0 days" in capsys.readouterr().out


def test_streak_command_rejects_bad_days(capsys):
    handle_streak(TaskManager(Database(":memory:")), Namespace(days=0, json=False))

    assert "at least 1" in capsys.readouterr().out
