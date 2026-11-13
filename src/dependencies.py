from collections import deque
from typing import Dict, Iterable, List, Optional, Tuple

from src.models.task import Task


def _blockers_map(edges: Iterable[Tuple[int, int]]) -> Dict[int, List[int]]:
    mapping: Dict[int, List[int]] = {}

    for task_id, depends_on in edges:
        mapping.setdefault(task_id, []).append(depends_on)

    return mapping


def find_path(
    edges: Iterable[Tuple[int, int]], start: int, goal: int
) -> Optional[List[int]]:
    """Shortest chain start -> ... -> goal following "depends on" links.

    `edges` holds (task_id, depends_on) pairs. Returns the list of task IDs
    from `start` to `goal`, or None if `start` does not depend on `goal`,
    directly or through other tasks.
    """
    blockers = _blockers_map(edges)
    queue = deque([[start]])
    seen = {start}

    while queue:
        path = queue.popleft()

        if path[-1] == goal and len(path) > 1:
            return path

        for next_id in blockers.get(path[-1], []):
            if next_id == goal:
                return path + [next_id]

            if next_id not in seen:
                seen.add(next_id)
                queue.append(path + [next_id])

    return None


def find_cycle_if_added(
    edges: Iterable[Tuple[int, int]], task_id: int, depends_on: int
) -> Optional[List[int]]:
    """The loop that adding "task_id depends on depends_on" would create.

    A loop appears exactly when `depends_on` already depends, directly or
    indirectly, on `task_id`. Returns the loop as [task_id, depends_on, ...,
    task_id], or None if the new link is safe.
    """
    if task_id == depends_on:
        return [task_id, task_id]

    path = find_path(edges, depends_on, task_id)

    if path is None:
        return None

    return [task_id] + path


class DependencyManager:
    """Link tasks so that one cannot be finished before another."""

    def __init__(self, database):
        self.database = database

    def add(self, task_id: int, blocker_id: int) -> None:
        """Make `task_id` wait for `blocker_id`.

        Raises ValueError for unknown tasks, self-links, repeated links and
        links that would create a loop (A waits on B, B waits on A).
        """
        for number in (task_id, blocker_id):
            if self.database.get_task(number) is None:
                raise ValueError(f"Task {number} not found.")

        if task_id == blocker_id:
            raise ValueError("A task cannot depend on itself.")

        if blocker_id in self.database.get_blocker_ids(task_id):
            raise ValueError(
                f"Task {task_id} already depends on task {blocker_id}."
            )

        loop = find_cycle_if_added(
            self.database.get_all_dependencies(), task_id, blocker_id
        )
        if loop:
            chain = " -> ".join(str(number) for number in loop)
            raise ValueError(
                f"That would create a circular dependency: {chain}"
            )

        self.database.add_dependency(task_id, blocker_id)

    def remove(self, task_id: int, blocker_id: int) -> None:
        """Remove a link. Raises ValueError if the link does not exist."""
        if not self.database.remove_dependency(task_id, blocker_id):
            raise ValueError(
                f"Task {task_id} does not depend on task {blocker_id}."
            )

    def get_blockers(self, task_id: int, pending_only: bool = True) -> List[Task]:
        """Tasks that `task_id` is waiting on.

        By default only unfinished blockers are returned, because a
        completed blocker no longer holds anything up.
        """
        blockers = []

        for blocker_id in self.database.get_blocker_ids(task_id):
            blocker = self.database.get_task(blocker_id)

            if blocker is not None and not (pending_only and blocker.completed):
                blockers.append(blocker)

        return blockers

    def is_blocked(self, task_id: int) -> bool:
        """True if a pending task is waiting on at least one unfinished task."""
        task = self.database.get_task(task_id)

        return bool(task and not task.completed and self.get_blockers(task_id))

    def get_dependents(self, task_id: int, pending_only: bool = True) -> List[Task]:
        """Tasks that are waiting on `task_id`."""
        dependents = []

        for dependent_id in self.database.get_dependent_ids(task_id):
            dependent = self.database.get_task(dependent_id)

            if dependent is not None and not (pending_only and dependent.completed):
                dependents.append(dependent)

        return dependents

    def get_blocker_map(self) -> Dict[int, List[int]]:
        """{task_id: [unfinished blocker IDs]} for every blocked pending task."""
        tasks = {task.task_id: task for task in self.database.get_all_tasks()}
        blocked: Dict[int, List[int]] = {}

        for task_id, blocker_id in self.database.get_all_dependencies():
            task = tasks.get(task_id)
            blocker = tasks.get(blocker_id)

            if task and blocker and not task.completed and not blocker.completed:
                blocked.setdefault(task_id, []).append(blocker_id)

        return blocked

    def get_blocked_tasks(self) -> List[Task]:
        """Pending tasks that are waiting on at least one unfinished task."""
        blocked = self.get_blocker_map()

        return [
            task for task in self.database.get_all_tasks(completed=False)
            if task.task_id in blocked
        ]

    def get_ready_tasks(self) -> List[Task]:
        """Pending tasks with nothing unfinished standing in their way."""
        blocked = self.get_blocker_map()

        return [
            task for task in self.database.get_all_tasks(completed=False)
            if task.task_id not in blocked
        ]

    def get_newly_ready(self, completed_task_id: int) -> List[Task]:
        """Tasks freed up now that `completed_task_id` is done.

        Call this after completing a task. A waiting task only counts if
        that task was the last unfinished thing holding it up.
        """
        still_blocked = self.get_blocker_map()

        return [
            task for task in self.get_dependents(completed_task_id)
            if task.task_id not in still_blocked
        ]
