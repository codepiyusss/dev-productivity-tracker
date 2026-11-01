from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Task:
    title: str
    description: str = ""
    priority: str = "medium"
    category: str = "general"
    due_date: Optional[str] = None
    completed: bool = False
    task_id: Optional[int] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.title.strip():
            raise ValueError("Task title cannot be empty.")

        if self.priority not in {"low", "medium", "high"}:
            raise ValueError("Priority must be low, medium, or high.")

        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")

    def mark_completed(self):
        self.completed = True

    def mark_pending(self):
        self.completed = False

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "category": self.category,
            "due_date": self.due_date,
            "completed": self.completed,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
