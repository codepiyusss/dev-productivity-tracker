from datetime import date, datetime
from typing import Dict, List, Optional

from src.models.task import Task


def _completed_on(task: Task) -> Optional[date]:
    try:
        return datetime.fromisoformat(task.completed_at).date() if task.completed_at else None
    except ValueError:
        return None


def find_purgeable(
    database,
    older_than_days: int,
    today: Optional[date] = None,
    include_undated: bool = False
) -> List[Task]:
    """Completed tasks that were finished at least `older_than_days` ago.

    Pending tasks are never included. Tasks completed before completion times
    were tracked (or with an unreadable timestamp) have no known date, so they
    are only included when `include_undated` is True. Oldest first.
    """
    if isinstance(older_than_days, bool) or not isinstance(older_than_days, int) or older_than_days < 1:
        raise ValueError("Days must be a whole number of at least 1.")

    today = today or date.today()
    dated, undated = [], []

    for task in database.get_all_tasks(completed=True):
        finished = _completed_on(task)

        if finished is None:
            undated.append(task)
        elif (today - finished).days >= older_than_days:
            dated.append((finished, task.task_id, task))

    result = [task for _, _, task in sorted(dated)]

    if include_undated:
        result.extend(sorted(undated, key=lambda task: task.task_id))

    return result


def describe_purge(database, tasks: List[Task]) -> Dict[str, int]:
    """What deleting `tasks` would remove, without deleting anything.

    Time entries, tags and dependency links are deleted along with their task.
    """
    entries = 0
    ids = {task.task_id for task in tasks}

    for task_id in ids:
        entries += len(database.get_time_entries(task_id=task_id))

    dependency_links = sum(
        1 for task_id, depends_on in database.get_all_dependencies()
        if task_id in ids or depends_on in ids
    )

    return {
        "tasks": len(ids),
        "time_entries": entries,
        "dependency_links": dependency_links,
    }


def purge_tasks(database, tasks: List[Task]) -> Dict[str, int]:
    """Permanently delete the given tasks and everything attached to them.

    Returns what was removed (see `describe_purge`). Callers should make a
    backup first; this cannot be undone.
    """
    summary = describe_purge(database, tasks)

    for task in tasks:
        database.delete_task(task.task_id)

    return summary
