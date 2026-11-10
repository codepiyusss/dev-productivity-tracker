from datetime import date
from typing import List, Optional, Tuple

from src.database import Database
from src.models.task import Task
from src.recurrence import next_due_date, validate_rule
from src.utils import validate_due_date

PRIORITIES = {"low", "medium", "high"}


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
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
        recurrence: Optional[str] = None
    ) -> Task:
        """Create and save a new task."""
        task = Task(
            title=title,
            description=description,
            priority=priority,
            category=category,
            due_date=validate_due_date(due_date),
            tags=tags or [],
            recurrence=self._check_recurrence(
                recurrence, validate_due_date(due_date)
            )
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
            "due_date",
            "recurrence"
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

        if "title" in updates and not str(updates["title"]).strip():
            raise ValueError("Task title cannot be empty.")

        if "priority" in updates and updates["priority"] not in PRIORITIES:
            raise ValueError("Priority must be low, medium, or high.")

        if "due_date" in updates:
            updates["due_date"] = validate_due_date(updates["due_date"])

        if "recurrence" in updates or "due_date" in updates:
            updates["recurrence"] = self._check_recurrence(
                updates.get("recurrence", task.recurrence),
                updates.get("due_date", task.due_date),
            )

        for field, value in updates.items():
            setattr(task, field, value)

        self.database.update_task(task)
        return task

    @staticmethod
    def _check_recurrence(rule, due_date):
        """Validate a repeat rule. Repeating tasks need a due date."""
        rule = validate_rule(rule)

        if rule and not due_date:
            raise ValueError(
                "A repeating task needs a due date, so it knows when to repeat."
            )

        return rule

    def add_tags(self, task_id: int, tags: List[str]) -> Optional[Task]:
        """Add one or more tags to a task. Returns None if task not found."""
        task = self.get_task(task_id)

        if task is None:
            return None

        for tag in tags:
            task.add_tag(tag)

        self.database.update_task(task)
        return task

    def remove_tags(self, task_id: int, tags: List[str]) -> Optional[Task]:
        """Remove one or more tags from a task. Returns None if not found."""
        task = self.get_task(task_id)

        if task is None:
            return None

        for tag in tags:
            task.remove_tag(tag)

        self.database.update_task(task)
        return task

    def get_all_tags(self) -> dict:
        """Return every tag in use with its task count."""
        return self.database.get_tag_counts()

    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed."""
        task = self.get_task(task_id)

        if task is None:
            return False

        task.mark_completed()
        return self.database.update_task(task)

    def complete_with_recurrence(
        self, task_id: int, today: Optional[date] = None
    ) -> Tuple[bool, Optional[Task]]:
        """Complete a task and, if it repeats, create the next occurrence.

        Returns (completed, next_task). `next_task` is None for tasks that do
        not repeat, for tasks that were already completed, and when an
        identical pending occurrence already exists (for example after
        reopening and completing the same task again).
        """
        task = self.get_task(task_id)

        if task is None:
            return False, None

        was_completed = task.completed
        task.mark_completed()
        self.database.update_task(task)

        if was_completed or not task.recurrence or not task.due_date:
            return True, None

        try:
            due = date.fromisoformat(task.due_date)
        except ValueError:
            return True, None  # unreadable legacy date: cannot schedule

        next_due = next_due_date(due, task.recurrence, today).isoformat()

        already_scheduled = any(
            other.title == task.title
            and other.category == task.category
            and other.due_date == next_due
            for other in self.database.get_all_tasks(completed=False)
        )

        if already_scheduled:
            return True, None

        return True, self.create_task(
            task.title,
            description=task.description,
            priority=task.priority,
            category=task.category,
            due_date=next_due,
            tags=list(task.tags),
            recurrence=task.recurrence,
        )

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
