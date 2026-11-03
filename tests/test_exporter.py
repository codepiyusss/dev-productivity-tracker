import csv
import json

import pytest

from src.database import Database
from src.exporter import (
    CSV_FIELDS, export_tasks, export_tasks_csv, export_tasks_json,
)
from src.tasks import TaskManager


@pytest.fixture
def tasks():
    manager = TaskManager(Database(":memory:"))
    manager.create_task(
        "Ship release, v2", description='Say "hello"\nsecond line',
        priority="high", category="work", due_date="2026-12-01",
        tags=["work", "urgent"],
    )
    done = manager.create_task("Café ☕ task")
    manager.complete_task(done.task_id)
    return manager.get_all_tasks()


def test_json_export_contains_all_fields_and_tags(tasks, tmp_path):
    path = export_tasks_json(tasks, str(tmp_path / "out.json"))

    data = json.loads(open(path, encoding="utf-8").read())

    assert len(data) == 2
    release = next(t for t in data if t["title"].startswith("Ship"))
    assert release["tags"] == ["work", "urgent"]
    assert release["priority"] == "high"
    assert release["completed"] is False


def test_json_export_keeps_unicode(tasks, tmp_path):
    path = export_tasks_json(tasks, str(tmp_path / "out.json"))
    assert "Café ☕ task" in open(path, encoding="utf-8").read()


def test_csv_export_has_header_and_rows(tasks, tmp_path):
    path = export_tasks_csv(tasks, str(tmp_path / "out.csv"))

    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert reader.fieldnames == CSV_FIELDS
    assert len(rows) == 2


def test_csv_export_escapes_commas_quotes_and_newlines(tasks, tmp_path):
    path = export_tasks_csv(tasks, str(tmp_path / "out.csv"))

    with open(path, encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    release = next(r for r in rows if r["title"].startswith("Ship"))
    assert release["title"] == "Ship release, v2"
    assert release["description"] == 'Say "hello"\nsecond line'
    assert release["tags"] == "work;urgent"
    assert release["completed"] == "no"


def test_csv_export_marks_completed_and_empty_tags(tasks, tmp_path):
    path = export_tasks_csv(tasks, str(tmp_path / "out.csv"))

    with open(path, encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    cafe = next(r for r in rows if r["title"].startswith("Caf"))
    assert cafe["completed"] == "yes"
    assert cafe["tags"] == ""


def test_export_empty_list_writes_header_only(tmp_path):
    path = export_tasks_csv([], str(tmp_path / "empty.csv"))
    lines = open(path, encoding="utf-8").read().strip().splitlines()
    assert lines == [",".join(CSV_FIELDS)]

    json_path = export_tasks_json([], str(tmp_path / "empty.json"))
    assert json.loads(open(json_path, encoding="utf-8").read()) == []


def test_export_creates_missing_folders(tasks, tmp_path):
    path = export_tasks(tasks, str(tmp_path / "a" / "b" / "out.json"), "json")
    assert json.loads(open(path, encoding="utf-8").read())


def test_export_tasks_dispatches_by_format_case_insensitively(tasks, tmp_path):
    path = export_tasks(tasks, str(tmp_path / "out.csv"), "CSV")
    assert open(path, encoding="utf-8").read().startswith("task_id,title")


def test_export_rejects_unknown_format(tasks, tmp_path):
    with pytest.raises(ValueError):
        export_tasks(tasks, str(tmp_path / "out.xml"), "xml")
