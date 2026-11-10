import sqlite3

from src.database import Database
from src.exporter import export_tasks_csv
from src.models.task import Task
from src.tasks import TaskManager


def test_new_task_has_no_recurrence():
    assert Task("Write docs").recurrence is None


def test_recurrence_is_saved_and_loaded():
    database = Database(":memory:")
    database.add_task(Task("Standup", due_date="2026-11-10", recurrence="daily"))

    assert database.get_all_tasks()[0].recurrence == "daily"


def test_recurrence_survives_other_updates():
    database = Database(":memory:")
    task = database.add_task(Task("Standup", due_date="2026-11-10", recurrence="weekly"))

    task.mark_completed()
    database.update_task(task)

    assert database.get_task(task.task_id).recurrence == "weekly"


def test_recurrence_can_be_cleared():
    database = Database(":memory:")
    task = database.add_task(Task("Standup", recurrence="daily"))

    task.recurrence = None
    database.update_task(task)

    assert database.get_task(task.task_id).recurrence is None


def test_to_dict_and_from_dict_keep_recurrence():
    task = Task("Standup", recurrence="monthly")

    assert Task.from_dict(task.to_dict()).recurrence == "monthly"


def test_database_without_recurrence_column_migrates(tmp_path):
    path = str(tmp_path / "old.db")
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("""
            CREATE TABLE tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'medium',
                category TEXT NOT NULL DEFAULT 'general',
                due_date TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        connection.execute(
            "INSERT INTO tasks (title, created_at) VALUES (?, ?)",
            ("Legacy", "2026-01-01T00:00:00")
        )
    connection.close()

    manager = TaskManager(Database(path))
    legacy = manager.get_all_tasks()[0]

    assert (legacy.title, legacy.recurrence) == ("Legacy", None)

    legacy.recurrence = "weekly"
    manager.database.update_task(legacy)
    assert TaskManager(Database(path)).get_task(legacy.task_id).recurrence == "weekly"


def test_csv_export_still_works_with_the_new_field(tmp_path):
    database = Database(":memory:")
    database.add_task(Task("Standup", recurrence="daily"))

    path = export_tasks_csv(database.get_all_tasks(), str(tmp_path / "x.csv"))

    assert "recurrence" in open(path, encoding="utf-8").readline()
