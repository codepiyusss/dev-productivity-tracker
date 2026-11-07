import sqlite3

from src.database import Database
from src.models.task import Task
from src.tasks import TaskManager


def test_completing_task_saves_completion_time():
    manager = TaskManager(Database(":memory:"))
    task = manager.create_task("Ship release")

    manager.complete_task(task.task_id)

    saved = manager.get_task(task.task_id)
    assert saved.completed is True
    assert saved.completed_at is not None


def test_reopening_task_clears_completion_time():
    manager = TaskManager(Database(":memory:"))
    task = manager.create_task("Ship release")
    manager.complete_task(task.task_id)

    manager.reopen_task(task.task_id)

    saved = manager.get_task(task.task_id)
    assert saved.completed is False
    assert saved.completed_at is None


def test_pending_task_has_no_completion_time():
    manager = TaskManager(Database(":memory:"))
    task = manager.create_task("Ship release")

    assert manager.get_task(task.task_id).completed_at is None


def test_get_all_tasks_returns_completion_time():
    database = Database(":memory:")
    database.add_task(Task("Done", completed=True,
                           completed_at="2026-11-10T09:30:00"))

    assert database.get_all_tasks()[0].completed_at == "2026-11-10T09:30:00"


def test_database_created_before_completed_at_migrates(tmp_path):
    db_file = str(tmp_path / "old.db")

    # Schema exactly as it was before this column existed.
    connection = sqlite3.connect(db_file)
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
                created_at TEXT NOT NULL
            )
        """)
        connection.execute(
            "INSERT INTO tasks (title, completed, created_at) VALUES (?, ?, ?)",
            ("Legacy done", 1, "2026-01-01T00:00:00")
        )
    connection.close()

    manager = TaskManager(Database(db_file))
    legacy = manager.get_all_tasks()[0]

    assert legacy.title == "Legacy done"
    assert legacy.completed is True
    assert legacy.completed_at is None  # unknown for old rows

    new_task = manager.create_task("New")
    manager.complete_task(new_task.task_id)
    assert manager.get_task(new_task.task_id).completed_at is not None

    # Opening an already-migrated database again must not fail.
    assert len(TaskManager(Database(db_file)).get_all_tasks()) == 2
