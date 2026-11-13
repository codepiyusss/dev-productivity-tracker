from collections import deque
from typing import Dict, Iterable, List, Optional, Tuple


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
