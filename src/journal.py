import sqlite3
from datetime import datetime, date
from pathlib import Path


class ProductivityJournal:
    def __init__(self, db_path="data/productivity.db"):
        self.db_path = db_path

        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._keeper = None
        if db_path == ":memory:":
            import uuid
            self.db_path = (
                f"file:journal_{uuid.uuid4().hex}?mode=memory&cache=shared"
            )
            self._keeper = sqlite3.connect(self.db_path, uri=True)

        self.initialize()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            uri=self.db_path.startswith("file:")
        )
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_date TEXT NOT NULL UNIQUE,
                    achievements TEXT NOT NULL DEFAULT '',
                    challenges TEXT NOT NULL DEFAULT '',
                    next_steps TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def add_entry(
        self,
        achievements="",
        challenges="",
        next_steps="",
        entry_date=None
    ):
        entry_date = entry_date or date.today().isoformat()

        try:
            date.fromisoformat(entry_date)
        except ValueError:
            raise ValueError("Date must use YYYY-MM-DD format.")

        now = datetime.now().isoformat(timespec="seconds")

        with self._connect() as connection:
            connection.execute("""
                INSERT INTO journal_entries (
                    entry_date, achievements, challenges,
                    next_steps, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry_date, achievements, challenges,
                next_steps, now, now
            ))

        return self.get_entry(entry_date)

    def get_entry(self, entry_date):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM journal_entries WHERE entry_date = ?",
                (entry_date,)
            ).fetchone()

        return dict(row) if row else None

    def update_entry(
        self,
        entry_date,
        achievements=None,
        challenges=None,
        next_steps=None
    ):
        existing = self.get_entry(entry_date)

        if existing is None:
            return False

        values = {
            "achievements": achievements if achievements is not None else existing["achievements"],
            "challenges": challenges if challenges is not None else existing["challenges"],
            "next_steps": next_steps if next_steps is not None else existing["next_steps"]
        }

        with self._connect() as connection:
            cursor = connection.execute("""
                UPDATE journal_entries
                SET achievements = ?, challenges = ?,
                    next_steps = ?, updated_at = ?
                WHERE entry_date = ?
            """, (
                values["achievements"],
                values["challenges"],
                values["next_steps"],
                datetime.now().isoformat(timespec="seconds"),
                entry_date
            ))

        return cursor.rowcount > 0

    def get_all_entries(self, limit=None,keyword=None,start_date=None, end_date=None):
        query = "SELECT * FROM journal_entries WHERE 1=1"
        parameters = []

        if keyword:
            query += """
                AND (
                    achievements LIKE ?
                    OR challenges LIKE ?
                    OR next_steps LIKE ?
                )
            """
            search = f"%{keyword}%"
            parameters.extend([search, search, search])

        if start_date:
            date.fromisoformat(start_date)
            query += " AND entry_date >= ?"
            parameters.append(start_date)

        if end_date:
            date.fromisoformat(end_date)
            query += " AND entry_date <= ?"
            parameters.append(end_date)

        query += " ORDER BY entry_date DESC"

        if limit is not None:
            if limit < 1:
                raise ValueError("Limit must be at least 1.")
            query += " LIMIT ?"
            parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [dict(row) for row in rows]

    def delete_entry(self, entry_date):
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM journal_entries WHERE entry_date = ?",
                (entry_date,)
            )

        return cursor.rowcount > 0
