from datetime import datetime
from typing import Dict, List, Optional

MAX_NOTE_LENGTH = 2000
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"


class NoteManager:
    """Short timestamped notes attached to tasks."""

    def __init__(self, database):
        self.database = database

    def add(self, task_id: int, text: str, now: Optional[datetime] = None) -> Dict:
        """Attach a note to a task. Raises ValueError for bad input."""
        if self.database.get_task(task_id) is None:
            raise ValueError(f"Task {task_id} not found.")

        cleaned = str(text or "").strip()

        if not cleaned:
            raise ValueError("A note cannot be empty.")

        if len(cleaned) > MAX_NOTE_LENGTH:
            raise ValueError(
                f"A note cannot be longer than {MAX_NOTE_LENGTH} characters "
                f"(this one has {len(cleaned)})."
            )

        stamp = (now or datetime.now()).strftime(TIMESTAMP_FORMAT)
        return self.database.add_note(task_id, cleaned, stamp)

    def list(self, task_id: int) -> List[Dict]:
        """A task's notes, oldest first."""
        return self.database.get_notes(task_id)

    def delete(self, note_id: int) -> Dict:
        """Delete a note and return it. Raises ValueError if it does not exist."""
        note = self.database.get_note(note_id)

        if note is None:
            raise ValueError(f"Note {note_id} not found.")

        self.database.delete_note(note_id)
        return note
