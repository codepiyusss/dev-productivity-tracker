import csv
import json
from pathlib import Path
from typing import Iterable, List

from src.models.task import Task

CSV_FIELDS = [
    "task_id", "title", "description", "priority", "category",
    "due_date", "completed", "created_at", "tags",
]
TAG_SEPARATOR = ";"
SUPPORTED_FORMATS = ("csv", "json")


def _prepare_output(output_path: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def export_tasks_json(tasks: Iterable[Task], output_path: str) -> str:
    """Write tasks to a JSON file and return the file path."""
    path = _prepare_output(output_path)
    data = [task.to_dict() for task in tasks]

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    return str(path)


def export_tasks_csv(tasks: Iterable[Task], output_path: str) -> str:
    """Write tasks to a CSV file and return the file path.

    Tags are joined with ';' in a single column so the file stays flat
    and can be read back by a CSV import.
    """
    path = _prepare_output(output_path)

    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for task in tasks:
            row = task.to_dict()
            row["tags"] = TAG_SEPARATOR.join(task.tags)
            row["completed"] = "yes" if task.completed else "no"
            writer.writerow(row)

    return str(path)


def export_tasks(tasks: List[Task], output_path: str, file_format: str) -> str:
    """Export tasks in the requested format ('csv' or 'json')."""
    file_format = file_format.casefold()

    if file_format == "csv":
        return export_tasks_csv(tasks, output_path)

    if file_format == "json":
        return export_tasks_json(tasks, output_path)

    raise ValueError(
        f"Unsupported export format: {file_format}. "
        f"Choose from: {', '.join(SUPPORTED_FORMATS)}."
    )
