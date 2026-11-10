import json

import pytest

from src.database import Database
from src.exporter import export_tasks
from src.importer import import_tasks_csv
from src.tasks import TaskManager


@pytest.fixture
def manager():
    return TaskManager(Database(":memory:"))


def write_csv(tmp_path, text):
    path = tmp_path / "in.csv"
    path.write_text(text, encoding="utf-8", newline="")
    return str(path)


def test_import_reads_the_recurrence_column(manager, tmp_path):
    path = write_csv(tmp_path, (
        "title,due_date,recurrence\n"
        "Standup,2026-12-01,Daily\n"
        "One-off,2026-12-02,\n"
    ))

    result = import_tasks_csv(path, manager)

    assert (result.imported, result.failed) == (2, 0)
    rules = {t.title: t.recurrence for t in manager.get_all_tasks()}
    assert rules == {"Standup": "daily", "One-off": None}


def test_import_rejects_unknown_rules_and_missing_due_dates(manager, tmp_path):
    path = write_csv(tmp_path, (
        "title,due_date,recurrence\n"
        "Bad rule,2026-12-01,yearly\n"
        "No date,,weekly\n"
        "Good,2026-12-01,weekly\n"
    ))

    result = import_tasks_csv(path, manager)

    assert (result.imported, result.failed) == (1, 2)
    assert "daily, weekly, monthly" in result.errors[0]
    assert "needs a due date" in result.errors[1]


def test_dry_run_checks_recurrence_too(manager, tmp_path):
    path = write_csv(tmp_path, "title,recurrence\nNo date,weekly\n")

    result = import_tasks_csv(path, manager, dry_run=True)

    assert result.failed == 1
    assert manager.get_all_tasks() == []


def test_csv_files_without_the_column_still_import(manager, tmp_path):
    result = import_tasks_csv(write_csv(tmp_path, "title\nPlain\n"), manager)

    assert result.imported == 1
    assert manager.get_all_tasks()[0].recurrence is None


def test_export_then_import_keeps_the_repeat_rule(tmp_path):
    source = TaskManager(Database(":memory:"))
    source.create_task("Standup", due_date="2026-12-01", recurrence="weekly")
    source.create_task("Plain")
    path = export_tasks(source.get_all_tasks(), str(tmp_path / "x.csv"), "csv")

    target = TaskManager(Database(":memory:"))
    result = import_tasks_csv(path, target)

    assert (result.imported, result.failed) == (2, 0)
    rules = {t.title: t.recurrence for t in target.get_all_tasks()}
    assert rules == {"Standup": "weekly", "Plain": None}


def test_json_export_includes_recurrence(tmp_path):
    source = TaskManager(Database(":memory:"))
    source.create_task("Standup", due_date="2026-12-01", recurrence="daily")

    path = export_tasks(source.get_all_tasks(), str(tmp_path / "x.json"), "json")

    assert json.loads(open(path, encoding="utf-8").read())[0]["recurrence"] == "daily"
