from datetime import date, timedelta
from typing import List, Optional
from src.models.task import Task
from src.utils import normalize_tags


def filter_tasks(
    tasks: List[Task],
    keyword: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
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
        result = [t for t in result if t.priority.casefold() == priority.casefold()]

    if category:
        result = [t for t in result if t.category.casefold() == category.casefold()]

    if tags:
        wanted = normalize_tags(tags)
        result = [t for t in result if all(tag in t.tags for tag in wanted)]

    if status == "completed":
        result = [t for t in result if t.completed]
    elif status == "pending":
        result = [t for t in result if not t.completed]
    elif status is not None:
        raise ValueError("Status must be completed or pending.")

    sort_fields = {
        "title": lambda t: t.title.casefold(),
        "priority": lambda t: t.priority.casefold(),
        "category": lambda t: t.category.casefold(),
        "created_at": lambda t: t.created_at,
        "due_date": lambda t: t.due_date or "9999-12-31"
    }

    if sort_by not in sort_fields:
        raise ValueError(f"Unsupported sort field: {sort_by}")

    return sorted(result, key=sort_fields[sort_by], reverse=descending)


DUE_MODES = ("overdue", "today", "within", "none")


def _due_date(task: Task) -> Optional[date]:
    try:
        return date.fromisoformat(task.due_date) if task.due_date else None
    except ValueError:
        return None


def filter_by_due(
    tasks: List[Task],
    mode: str,
    days: Optional[int] = None,
    today: Optional[date] = None
) -> List[Task]:
    """Pending tasks selected by due date.

    mode:
      "overdue" - due before today
      "today"   - due today
      "within"  - due from today up to `days` days ahead (inclusive)
      "none"    - no due date at all
    Completed tasks are never returned, and tasks whose due date cannot be
    read are left out of the date-based modes.
    """
    if mode not in DUE_MODES:
        raise ValueError(f"Due filter must be one of: {', '.join(DUE_MODES)}.")

    if mode == "within" and (isinstance(days, bool) or not isinstance(days, int) or days < 0):
        raise ValueError("Days must be a whole number of at least 0.")

    today = today or date.today()
    last_day = today + timedelta(days=days) if mode == "within" else None
    selected = []

    for task in tasks:
        if task.completed:
            continue

        due = _due_date(task)

        if mode == "none":
            if not task.due_date:
                selected.append(task)
        elif due is None:
            continue
        elif mode == "overdue" and due < today:
            selected.append(task)
        elif mode == "today" and due == today:
            selected.append(task)
        elif mode == "within" and today <= due <= last_day:
            selected.append(task)

    return selected
