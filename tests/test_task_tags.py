import sqlite3

import pytest

from src.database import Database
from src.models.task import Task
from src.task_filters import filter_tasks
from src.tasks import TaskManager
from src.utils import normalize_tag, parse_tag_string


@pytest.fixture
def manager():
    return TaskManager(Database(":memory:"))


# ---- normalization ----

def test_normalize_tag_cleans_input():
    assert normalize_tag("  #Work  ") == "work"
    assert normalize_tag("Deep   Work") == "deep work"


@pytest.mark.parametrize("bad", ["", "   ", "#", "a,b", "x" * 31])
def test_normalize_tag_rejects_invalid(bad):
    with pytest.raises(ValueError):
        normalize_tag(bad)


def test_parse_tag_string_dedupes_and_skips_blanks():
    assert parse_tag_string("Work, urgent,, WORK ") == ["work", "urgent"]
    assert parse_tag_string(None) == []


# ---- model ----

def test_task_defaults_to_no_tags():
    assert Task("Write docs").tags == []


def test_task_tags_are_normalized_and_deduplicated():
    task = Task("Write docs", tags=["Docs", "#docs", "Writing"])
    assert task.tags == ["docs", "writing"]


def test_task_add_and_remove_tag():
    task = Task("Write docs")

    assert task.add_tag("Docs") is True
    assert task.add_tag("docs") is False
    assert task.has_tag("DOCS")
    assert task.remove_tag("docs") is True
    assert task.remove_tag("docs") is False
    assert task.tags == []


def test_task_to_dict_and_from_dict_keep_tags():
    task = Task("Write docs", tags=["docs"])
    assert Task.from_dict(task.to_dict()).tags == ["docs"]


# ---- persistence ----

def test_create_task_with_tags_persists(manager):
    task = manager.create_task("Ship release", tags=["work", "Urgent"])

    loaded = manager.get_task(task.task_id)
    assert loaded.tags == ["work", "urgent"]


def test_get_all_tasks_includes_tags(manager):
    manager.create_task("A", tags=["one"])
    manager.create_task("B")

    tags_by_title = {t.title: t.tags for t in manager.get_all_tasks()}
    assert tags_by_title == {"A": ["one"], "B": []}


def test_add_tags_to_existing_task(manager):
    task = manager.create_task("Ship release", tags=["work"])

    updated = manager.add_tags(task.task_id, ["urgent", "work"])

    assert updated.tags == ["work", "urgent"]
    assert manager.get_task(task.task_id).tags == ["work", "urgent"]


def test_remove_tags_from_task(manager):
    task = manager.create_task("Ship release", tags=["work", "urgent"])

    updated = manager.remove_tags(task.task_id, ["urgent", "missing"])

    assert updated.tags == ["work"]
    assert manager.get_task(task.task_id).tags == ["work"]


def test_tag_operations_on_missing_task_return_none(manager):
    assert manager.add_tags(999, ["x"]) is None
    assert manager.remove_tags(999, ["x"]) is None


def test_invalid_tag_does_not_change_task(manager):
    task = manager.create_task("Ship release", tags=["work"])

    with pytest.raises(ValueError):
        manager.add_tags(task.task_id, ["ok", ""])

    assert manager.get_task(task.task_id).tags == ["work"]


def test_updating_other_fields_keeps_tags(manager):
    task = manager.create_task("Ship release", tags=["work"])

    manager.update_task(task.task_id, title="Ship v2")
    manager.complete_task(task.task_id)

    assert manager.get_task(task.task_id).tags == ["work"]


def test_deleting_task_removes_its_tags(manager):
    task = manager.create_task("Ship release", tags=["work"])

    manager.delete_task(task.task_id)

    assert manager.get_all_tags() == {}


def test_get_all_tags_counts_tasks(manager):
    manager.create_task("A", tags=["work", "urgent"])
    manager.create_task("B", tags=["work"])

    assert manager.get_all_tags() == {"urgent": 1, "work": 2}


# ---- filtering ----

def test_filter_by_single_tag(manager):
    manager.create_task("A", tags=["work"])
    manager.create_task("B", tags=["home"])

    result = filter_tasks(manager.get_all_tasks(), tags=["WORK"])

    assert [t.title for t in result] == ["A"]


def test_filter_by_multiple_tags_requires_all(manager):
    manager.create_task("A", tags=["work", "urgent"])
    manager.create_task("B", tags=["work"])

    result = filter_tasks(manager.get_all_tasks(), tags=["work", "urgent"])

    assert [t.title for t in result] == ["A"]


def test_filter_without_tags_returns_everything(manager):
    manager.create_task("A", tags=["work"])
    manager.create_task("B")

    assert len(filter_tasks(manager.get_all_tasks())) == 2


# ---- migration ----

def test_existing_database_without_tags_migrates_safely(tmp_path):
    db_file = str(tmp_path / "old.db")

    # Build a database exactly as it looked before tags existed.
    with sqlite3.connect(db_file) as connection:
        connection.execute("""
            CREATE TABLE tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'medium',
                category TEXT NOT NULL DEFAULT 'general',
                due_date TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute(
            "INSERT INTO tasks (title, created_at) VALUES (?, ?)",
            ("Legacy task", "2026-01-01T00:00:00")
        )
    connection.close()

    manager = TaskManager(Database(db_file))
    legacy = manager.get_all_tasks()[0]

    assert legacy.title == "Legacy task"
    assert legacy.tags == []

    manager.add_tags(legacy.task_id, ["migrated"])
    assert manager.get_task(legacy.task_id).tags == ["migrated"]

    # Re-opening an already migrated database must also work.
    assert TaskManager(Database(db_file)).get_task(legacy.task_id).tags == ["migrated"]
