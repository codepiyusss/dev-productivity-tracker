from typing import List, Optional

from src.database import Database
from src.models.task import Task


class TaskManager:
    """Provides task management operations."""

    def __init__(self, database: Optional[Database] = None):
        self.database = database or Database()

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        category: str = "general",
        due_date: Optional[str] = None
    ) -> Task:
        """Create and save a new task."""
        task = Task(
            title=title,
            description=description,
            priority=priority,
            category=category,
            due_date=due_date
        )
        return self.database.add_task(task)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Retrieve a task by ID."""
        return self.database.get_task(task_id)

    def get_all_tasks(self) -> List[Task]:
        """Retrieve every task."""
        return self.database.get_all_tasks()

    def get_pending_tasks(self) -> List[Task]:
        """Retrieve incomplete tasks."""
        return self.database.get_all_tasks(completed=False)

    def get_completed_tasks(self) -> List[Task]:
        """Retrieve completed tasks."""
        return self.database.get_all_tasks(completed=True)

    def update_task(
        self,
        task_id: int,
        **updates
    ) -> Optional[Task]:
        """Update supported fields of an existing task."""
        allowed_fields = {
            "title",
            "description",
            "priority",
            "category",
            "due_date"
        }

        if not updates:
            raise ValueError("Provide at least one field to update.")

        invalid_fields = set(updates) - allowed_fields
        if invalid_fields:
            raise ValueError(
                f"Unsupported fields: {', '.join(sorted(invalid_fields))}"
            )

        task = self.get_task(task_id)

        if task is None:
            return None

        for field, value in updates.items():
            setattr(task, field, value)

        self.database.update_task(task)
        return task

    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed."""
        task = self.get_task(task_id)

        if task is None:
            return False

        task.mark_completed()
        return self.database.update_task(task)

    def reopen_task(self, task_id: int) -> bool:
        """Move a completed task back to pending."""
        task = self.get_task(task_id)

        if task is None:
            return False

        task.mark_pending()
        return self.database.update_task(task)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        return self.database.delete_task(task_id)

    def get_task_count(self) -> dict:
        """Return total, pending, and completed task counts."""
        all_tasks = self.get_all_tasks()

        completed = sum(task.completed for task in all_tasks)
        total = len(all_tasks)

        return {
            "total": total,
            "completed": completed,
            "pending": total - completed
        }
