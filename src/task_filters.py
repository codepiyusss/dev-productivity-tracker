from typing import List, Optional
from src.models.task import Task


def filter_tasks(
    tasks: List[Task],
    keyword: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "created_at",
    descending: bool = True
) -> List[Task]:
    result = list(tasks)

    if keyword:
        keyword = keyword.casefold()
        result = [
            task for task in result
            if keyword in task.title.casefold()
            or keyword in task.description.casefold()
        ]

    if priority:
        result = [
            task for task in result
            if task.priority.casefold() == priority.casefold()
        ]

    if category:
        result = [
            task for task in result
            if task.category.casefold() == category.casefold()
        ]

    if status == "completed":
        result = [task for task in result if task.completed]
    elif status == "pending":
        result = [task for task in result if not task.completed]
    elif status is not None:
        raise ValueError("Status must be completed or pending.")

    sort_fields = {
        "title": lambda task: task.title.casefold(),
        "priority": lambda task: task.priority.casefold(),
        "category": lambda task: task.category.casefold(),
        "created_at": lambda task: task.created_at,
        "due_date": lambda task: task.due_date or "9999-12-31"
    }

    if sort_by not in sort_fields:
        raise ValueError(f"Unsupported sort field: {sort_by}")

    return sorted(result, key=sort_fields[sort_by], reverse=descending)
