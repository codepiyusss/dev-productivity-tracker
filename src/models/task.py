from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.utils import normalize_tags


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
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.title.strip():
            raise ValueError("Task title cannot be empty.")

        if self.priority not in {"low", "medium", "high"}:
            raise ValueError("Priority must be low, medium, or high.")

        self.tags = normalize_tags(self.tags)

        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")

    def mark_completed(self):
        """Complete the task and record when it happened (first time only)."""
        self.completed = True

        if not self.completed_at:
            self.completed_at = datetime.now().isoformat(timespec="seconds")

    def mark_pending(self):
        """Reopen the task and clear its completion time."""
        self.completed = False
        self.completed_at = None

    def add_tag(self, tag: str) -> bool:
        """Add a tag. Returns False if the task already had it."""
        (cleaned,) = normalize_tags([tag])

        if cleaned in self.tags:
            return False

        self.tags.append(cleaned)
        return True

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag. Returns False if the task did not have it."""
        (cleaned,) = normalize_tags([tag])

        if cleaned not in self.tags:
            return False

        self.tags.remove(cleaned)
        return True

    def has_tag(self, tag: str) -> bool:
        (cleaned,) = normalize_tags([tag])
        return cleaned in self.tags

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
            "completed_at": self.completed_at,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
