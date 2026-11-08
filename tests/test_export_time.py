import csv
import json
from datetime import datetime

import pytest

from src.database import Database
from src.exporter import export_tasks, export_tasks_csv, export_tasks_json
from src.importer import import_tasks_csv
from src.main import main
from src.tasks import TaskManager
from src.timetracking import TimeTracker

NOW = datetime(2026, 11, 10, 18, 0, 0)


@pytest.fixture
def setup():
    database = Database(":memory:")
    manager = TaskManager(database)
    manager.create_task("Timed")
    manager.create_task("Untimed")
    tracker = TimeTracker(database)
    tracker.log_manual(1, 1800, now=NOW)
    tracker.log_manual(1, 900, now=NOW)
    return manager, tracker


def test_totals_by_task_sums_entries(setup):
    _, tracker = setup

    assert tracker.totals_by_task(NOW) == {1: 2700}


def test_totals_by_task_includes_running_timer(setup):
    _, tracker = setup
    tracker.start(2, datetime(2026, 11, 10, 17, 0, 0))

    assert tracker.totals_by_task(NOW)[2] == 3600


def test_json_export_adds_time_only_when_requested(setup, tmp_path):
    manager, tracker = setup
    tasks = manager.get_all_tasks()

    plain = json.loads(open(export_tasks_json(tasks, str(tmp_path / "a.json")), encoding="utf-8").read())
    timed = json.loads(open(export_tasks_json(tasks, str(tmp_path / "b.json"), tracker.totals_by_task(NOW)), encoding="utf-8").read())

    assert all("time_spent_seconds" not in item for item in plain)
    assert {i["title"]: i["time_spent_seconds"] for i in timed} == {"Timed": 2700, "Untimed": 0}


def test_csv_export_adds_time_column_only_when_requested(setup, tmp_path):
    manager, tracker = setup
    tasks = manager.get_all_tasks()

    plain = export_tasks_csv(tasks, str(tmp_path / "a.csv"))
    timed = export_tasks(tasks, str(tmp_path / "b.csv"), "csv", tracker.totals_by_task(NOW))

    with open(plain, encoding="utf-8", newline="") as file:
        assert "time_spent_seconds" not in csv.DictReader(file).fieldnames
    with open(timed, encoding="utf-8", newline="") as file:
        rows = {r["title"]: r["time_spent_seconds"] for r in csv.DictReader(file)}
    assert rows == {"Timed": "2700", "Untimed": "0"}


def test_exported_time_column_does_not_break_import(setup, tmp_path):
    manager, tracker = setup
    path = export_tasks(manager.get_all_tasks(), str(tmp_path / "x.csv"), "csv", {1: 99})

    target = TaskManager(Database(":memory:"))
    result = import_tasks_csv(path, target)

    assert (result.imported, result.failed) == (2, 0)


def test_cli_include_time_flag(tmp_path, capsys):
    def run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    run("add", "Timed")
    run("timer", "log", "1", "1h")
    out = str(tmp_path / "out.json")
    capsys.readouterr()

    assert run("export", "--format", "json", "--output", out, "--include-time") == 0

    assert json.loads(open(out, encoding="utf-8").read())[0]["time_spent_seconds"] == 3600
    run("export", "--format", "json", "--output", out)
    assert "time_spent_seconds" not in json.loads(open(out, encoding="utf-8").read())[0]
