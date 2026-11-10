import sqlite3
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Optional

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
        connection.execute("PRAGMA foreign_keys = ON")
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
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    recurrence TEXT
                )
            """)
            # Migration: databases created before completion times were
            # tracked get the new column; existing rows keep NULL.
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(tasks)")
            }
            if "completed_at" not in columns:
                connection.execute(
                    "ALTER TABLE tasks ADD COLUMN completed_at TEXT"
                )
            # Migration: repeat rule for recurring tasks (NULL = no repeat).
            if "recurrence" not in columns:
                connection.execute(
                    "ALTER TABLE tasks ADD COLUMN recurrence TEXT"
                )
            # Migration: tags live in their own table, so existing
            # databases upgrade safely without altering the tasks table.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS task_tags (
                    task_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    PRIMARY KEY (task_id, tag),
                    FOREIGN KEY (task_id) REFERENCES tasks (task_id)
                        ON DELETE CASCADE
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_tags_tag "
                "ON task_tags (tag)"
            )
            # Migration: time tracking. At most one entry may be running
            # (ended_at IS NULL) at any moment; the partial unique index
            # enforces that in the database itself.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS time_entries (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    CHECK (ended_at IS NULL OR ended_at >= started_at),
                    FOREIGN KEY (task_id) REFERENCES tasks (task_id)
                        ON DELETE CASCADE
                )
            """)
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_one_running_timer "
                "ON time_entries ((ended_at IS NULL)) WHERE ended_at IS NULL"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_time_entries_task "
                "ON time_entries (task_id)"
            )
            # Migration: productivity goals (one target per period).
            connection.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    period TEXT PRIMARY KEY,
                    target INTEGER NOT NULL CHECK (target > 0)
                )
            """)

    def add_task(self, task: Task) -> Task:
        with self._connect() as connection:
            cursor = connection.execute("""
                INSERT INTO tasks (
                    title, description, priority, category,
                    due_date, completed, created_at, completed_at,
                    recurrence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.title, task.description, task.priority,
                task.category, task.due_date, int(task.completed),
                task.created_at, task.completed_at, task.recurrence
            ))
            task.task_id = cursor.lastrowid
            self._save_tags(connection, task.task_id, task.tags)
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None
            tags = self._load_tags(connection, [task_id]).get(task_id, [])
        return self._row_to_task(row, tags)

    def get_all_tasks(self, completed: Optional[bool] = None) -> List[Task]:
        query = "SELECT * FROM tasks"
        parameters = ()

        if completed is not None:
            query += " WHERE completed = ?"
            parameters = (int(completed),)

        query += " ORDER BY created_at DESC, task_id DESC"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
            tag_map = self._load_tags(
                connection, [row["task_id"] for row in rows]
            )

        return [
            self._row_to_task(row, tag_map.get(row["task_id"], []))
            for row in rows
        ]

    def update_task(self, task: Task) -> bool:
        if task.task_id is None:
            raise ValueError("Cannot update a task without a task_id.")

        with self._connect() as connection:
            cursor = connection.execute("""
                UPDATE tasks
                SET title = ?, description = ?, priority = ?,
                    category = ?, due_date = ?, completed = ?,
                    completed_at = ?, recurrence = ?
                WHERE task_id = ?
            """, (
                task.title, task.description, task.priority,
                task.category, task.due_date, int(task.completed),
                task.completed_at, task.recurrence, task.task_id
            ))

            if cursor.rowcount > 0:
                self._save_tags(connection, task.task_id, task.tags)

        return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE task_id = ?", (task_id,)
            )
        return cursor.rowcount > 0

    def add_time_entry(
        self, task_id: int, started_at: str, ended_at: Optional[str] = None
    ) -> Dict:
        """Insert a time entry. An entry without ended_at is a running timer."""
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO time_entries (task_id, started_at, ended_at) "
                "VALUES (?, ?, ?)",
                (task_id, started_at, ended_at)
            )
        return {
            "entry_id": cursor.lastrowid, "task_id": task_id,
            "started_at": started_at, "ended_at": ended_at,
        }

    def get_running_entry(self) -> Optional[Dict]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM time_entries WHERE ended_at IS NULL"
            ).fetchone()
        return dict(row) if row else None

    def end_time_entry(self, entry_id: int, ended_at: str) -> bool:
        """Stop a running entry. Returns False if it is missing or finished."""
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE time_entries SET ended_at = ? "
                "WHERE entry_id = ? AND ended_at IS NULL",
                (ended_at, entry_id)
            )
        return cursor.rowcount > 0

    def get_time_entries(
        self,
        task_id: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> List[Dict]:
        """Entries oldest first, optionally limited by task and start time."""
        query = "SELECT * FROM time_entries WHERE 1 = 1"
        parameters = []

        if task_id is not None:
            query += " AND task_id = ?"
            parameters.append(task_id)

        if since is not None:
            query += " AND started_at >= ?"
            parameters.append(since)

        if until is not None:
            query += " AND started_at < ?"
            parameters.append(until)

        query += " ORDER BY started_at, entry_id"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def get_time_entry(self, entry_id: int) -> Optional[Dict]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM time_entries WHERE entry_id = ?", (entry_id,)
            ).fetchone()
        return dict(row) if row else None

    def delete_time_entry(self, entry_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM time_entries WHERE entry_id = ?", (entry_id,)
            )
        return cursor.rowcount > 0

    def set_goal(self, period: str, target: int) -> None:
        """Create or replace the completion target for a period."""
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO goals (period, target) VALUES (?, ?)
                ON CONFLICT(period) DO UPDATE SET target = excluded.target
            """, (period, target))

    def get_goal(self, period: str) -> Optional[int]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT target FROM goals WHERE period = ?", (period,)
            ).fetchone()
        return row["target"] if row else None

    def get_goals(self) -> Dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT period, target FROM goals ORDER BY period"
            ).fetchall()
        return {row["period"]: row["target"] for row in rows}

    def clear_goal(self, period: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM goals WHERE period = ?", (period,)
            )
        return cursor.rowcount > 0

    def get_tag_counts(self) -> Dict[str, int]:
        """Return {tag: number_of_tasks}, sorted by tag name."""
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT tag, COUNT(*) AS total
                FROM task_tags
                GROUP BY tag
                ORDER BY tag
            """).fetchall()
        return {row["tag"]: row["total"] for row in rows}

    @staticmethod
    def _save_tags(connection, task_id: int, tags: Iterable[str]):
        connection.execute(
            "DELETE FROM task_tags WHERE task_id = ?", (task_id,)
        )
        connection.executemany(
            "INSERT OR IGNORE INTO task_tags (task_id, tag) VALUES (?, ?)",
            [(task_id, tag) for tag in tags]
        )

    @staticmethod
    def _load_tags(connection, task_ids: List[int]) -> Dict[int, List[str]]:
        tag_map: Dict[int, List[str]] = {}

        # Chunk to stay under SQLite's variable limit on large task lists.
        for start in range(0, len(task_ids), 500):
            chunk = task_ids[start:start + 500]
            placeholders = ", ".join("?" for _ in chunk)
            rows = connection.execute(
                f"SELECT task_id, tag FROM task_tags "
                f"WHERE task_id IN ({placeholders}) "
                f"ORDER BY rowid",
                chunk
            ).fetchall()

            for row in rows:
                tag_map.setdefault(row["task_id"], []).append(row["tag"])

        return tag_map

    @staticmethod
    def _row_to_task(row: sqlite3.Row, tags: Optional[List[str]] = None) -> Task:
        return Task(
            task_id=row["task_id"],
            title=row["title"],
            description=row["description"],
            priority=row["priority"],
            category=row["category"],
            due_date=row["due_date"],
            completed=bool(row["completed"]),
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            recurrence=row["recurrence"],
            tags=tags or []
        )