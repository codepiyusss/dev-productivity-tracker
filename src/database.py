import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional

from src.models.task import Task


class Database:
    def __init__(self, db_path: str = "data/productivity.db"):
        self._uri = db_path == ":memory:"

        if self._uri:
            self.db_path = (
                f"file:taskdb_{uuid.uuid4().hex}?mode=memory&cache=shared"
            )
            self._keeper = sqlite3.connect(self.db_path, uri=True)
        else:
            self.db_path = db_path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._keeper = None

        self.initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, uri=self._uri)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
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

    def add_task(self, task: Task) -> Task:
        with self._connect() as connection:
            cursor = connection.execute("""
                INSERT INTO tasks (
                    title, description, priority, category,
                    due_date, completed, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                task.title, task.description, task.priority,
                task.category, task.due_date, int(task.completed),
                task.created_at
            ))
            task.task_id = cursor.lastrowid
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return self._row_to_task(row) if row else None

    def get_all_tasks(self, completed: Optional[bool] = None) -> List[Task]:
        query = "SELECT * FROM tasks"
        parameters = ()

        if completed is not None:
            query += " WHERE completed = ?"
            parameters = (int(completed),)

        query += " ORDER BY created_at DESC, task_id DESC"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [self._row_to_task(row) for row in rows]

    def update_task(self, task: Task) -> bool:
        if task.task_id is None:
            raise ValueError("Cannot update a task without a task_id.")

        with self._connect() as connection:
            cursor = connection.execute("""
                UPDATE tasks
                SET title = ?, description = ?, priority = ?,
                    category = ?, due_date = ?, completed = ?
                WHERE task_id = ?
            """, (
                task.title, task.description, task.priority,
                task.category, task.due_date, int(task.completed),
                task.task_id
            ))

        return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE task_id = ?", (task_id,)
            )
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            task_id=row["task_id"],
            title=row["title"],
            description=row["description"],
            priority=row["priority"],
            category=row["category"],
            due_date=row["due_date"],
            completed=bool(row["completed"]),
            created_at=row["created_at"]
        )