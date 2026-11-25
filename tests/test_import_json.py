import json

import pytest

from src.database import Database
from src.exporter import export_tasks
from src.importer import import_tasks_json
from src.tasks import TaskManager


@pytest.fixture
def manager():
    return TaskManager(Database(":memory:"))


def write_json(tmp_path, data, name="in.json"):
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return str(path)


def test_imports_typed_json_values(manager, tmp_path):
    path = write_json(tmp_path, [
        {"title": "Write docs", "priority": "High", "category": "work",
         "due_date": "2026-12-01", "completed": False, "tags": ["docs", "work"]},
        {"title": "Done thing", "completed": True, "tags": "a;b", "description": "text"},
    ])

    result = import_tasks_json(path, manager)

    assert (result.imported, result.failed) == (2, 0)
    docs = next(t for t in manager.get_all_tasks() if t.title == "Write docs")
    assert (docs.priority, docs.category, docs.due_date) == ("high", "work", "2026-12-01")
    assert docs.tags == ["docs", "work"]
    done = next(t for t in manager.get_all_tasks() if t.title == "Done thing")
    assert done.completed is True and done.tags == ["a", "b"] and done.description == "text"


def test_null_values_and_unknown_keys_are_fine(manager, tmp_path):
    path = write_json(tmp_path, [
        {"title": "Plain", "due_date": None, "recurrence": None, "extra": [1, 2], "task_id": 99},
    ])

    result = import_tasks_json(path, manager)

    assert result.imported == 1
    task = manager.get_all_tasks()[0]
    assert (task.due_date, task.recurrence) == (None, None)


def test_recurrence_is_imported_and_validated(manager, tmp_path):
    path = write_json(tmp_path, [
        {"title": "Standup", "due_date": "2026-12-01", "recurrence": "daily"},
        {"title": "No date", "recurrence": "weekly"},
        {"title": "Bad rule", "due_date": "2026-12-01", "recurrence": "yearly"},
    ])

    result = import_tasks_json(path, manager)

    assert (result.imported, result.failed) == (1, 2)
    assert "Item 2: repeating task needs a due date" in result.errors
    assert any(e.startswith("Item 3:") and "daily, weekly, monthly" in e for e in result.errors)


def test_bad_items_are_reported_by_number_and_skipped(manager, tmp_path):
    path = write_json(tmp_path, [
        {"title": "Good"},
        {"title": ""},
        "just a string",
        {"title": "Bad priority", "priority": "urgent"},
        {"title": "Bad date", "due_date": "01/12/2026"},
        42,
        {"title": "Also good"},
    ])

    result = import_tasks_json(path, manager)

    assert (result.imported, result.failed) == (2, 5)
    assert result.errors[0] == "Item 2: title is empty"
    assert result.errors[1] == "Item 3: expected an object, not str"
    assert result.errors[4] == "Item 6: expected an object, not int"
    assert len(manager.get_all_tasks()) == 2


def test_duplicates_are_skipped_and_dry_run_saves_nothing(manager, tmp_path):
    manager.create_task("Existing", category="work")
    path = write_json(tmp_path, [{"title": "existing", "category": "WORK"}, {"title": "New"}])

    dry = import_tasks_json(path, manager, dry_run=True)
    assert (dry.imported, dry.duplicates) == (1, 1)
    assert len(manager.get_all_tasks()) == 1

    real = import_tasks_json(path, manager)
    assert (real.imported, real.duplicates) == (1, 1)
    assert len(import_tasks_json(path, manager, allow_duplicates=True).errors) == 0


def test_file_level_errors(manager, tmp_path):
    with pytest.raises(ValueError, match="not found"):
        import_tasks_json(str(tmp_path / "nope.json"), manager)
    with pytest.raises(ValueError, match="Invalid JSON at line 1"):
        import_tasks_json(write_json(tmp_path, "{not json", "bad.json"), manager)
    with pytest.raises(ValueError, match="must be a list of task objects"):
        import_tasks_json(write_json(tmp_path, {"title": "x"}, "obj.json"), manager)


def test_empty_list_imports_nothing(manager, tmp_path):
    result = import_tasks_json(write_json(tmp_path, []), manager)

    assert (result.imported, result.failed, result.duplicates) == (0, 0, 0)


def test_export_then_import_round_trip(tmp_path):
    source = TaskManager(Database(":memory:"))
    source.create_task("Ship, release", description='Say "hi"\nline two', priority="high",
                       category="work", due_date="2026-12-01", tags=["work", "urgent"],
                       recurrence="weekly")
    done = source.create_task("Café ☕")
    source.complete_task(done.task_id)
    path = export_tasks(source.get_all_tasks(), str(tmp_path / "x.json"), "json")

    target = TaskManager(Database(":memory:"))
    result = import_tasks_json(path, target)

    assert (result.imported, result.failed) == (2, 0)
    by_title = {t.title: t for t in target.get_all_tasks()}
    release = by_title["Ship, release"]
    assert release.description == 'Say "hi"\nline two'
    assert (release.priority, release.category, release.recurrence) == ("high", "work", "weekly")
    assert release.tags == ["work", "urgent"]
    assert by_title["Café ☕"].completed is True
    assert import_tasks_json(path, target).imported == 0      # second time: all duplicates


def test_utf8_bom_is_accepted(manager, tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps([{"title": "With BOM"}]).encode("utf-8"))

    assert import_tasks_json(str(path), manager).imported == 1
