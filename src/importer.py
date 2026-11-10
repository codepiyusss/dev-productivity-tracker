import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from src.constants import DATE_FORMAT
from src.models.task import Task
from src.recurrence import validate_rule
from src.tasks import TaskManager
from src.utils import parse_tag_string

TRUE_VALUES = {"yes", "y", "true", "1", "done", "completed"}
FALSE_VALUES = {"no", "n", "false", "0", "", "pending"}
KNOWN_COLUMNS = {
    "title", "description", "priority", "category",
    "due_date", "completed", "tags", "recurrence",
}


@dataclass
class ImportResult:
    imported: int = 0
    duplicates: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)


def _normalize_header(name) -> str:
    return str(name or "").strip().casefold().replace(" ", "_").replace("-", "_")


def _parse_completed(value: str) -> bool:
    cleaned = value.strip().casefold()

    if cleaned in TRUE_VALUES:
        return True

    if cleaned in FALSE_VALUES:
        return False

    raise ValueError(f"invalid completed value '{value}' (use yes/no)")


def _parse_due_date(value: str):
    value = value.strip()

    if not value:
        return None

    try:
        datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        raise ValueError(f"invalid due date '{value}' (use YYYY-MM-DD)")

    return value


def _parse_tags(value: str) -> List[str]:
    """Accept tags separated by ';' (our export format) or ','."""
    return parse_tag_string(value.replace(";", ","))


def _duplicate_key(title: str, category: str, due_date) -> tuple:
    return (title.strip().casefold(), category.strip().casefold(), due_date or "")


def import_tasks_csv(
    csv_path: str,
    manager: TaskManager,
    dry_run: bool = False,
    allow_duplicates: bool = False
) -> ImportResult:
    """Import tasks from a CSV file.

    Required column: title. Optional: description, priority, category,
    due_date, completed, tags. Other columns (such as task_id and
    created_at from an export) are ignored; imported tasks get new IDs.
    Bad rows are reported by line number and skipped, never aborting
    the rest of the import.
    """
    path = Path(csv_path)

    if not path.is_file():
        raise ValueError(f"File not found: {csv_path}")

    result = ImportResult()

    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV file is empty.")

        reader.fieldnames = [_normalize_header(n) for n in reader.fieldnames]

        if "title" not in reader.fieldnames:
            raise ValueError("CSV must contain a 'title' column.")

        seen = set()
        if not allow_duplicates:
            seen = {
                _duplicate_key(t.title, t.category, t.due_date)
                for t in manager.get_all_tasks()
            }

        for row in reader:
            line = reader.line_num
            values = {
                key: (value or "").strip()
                for key, value in row.items()
                if key in KNOWN_COLUMNS
            }

            try:
                title = values.get("title", "")
                if not title:
                    raise ValueError("title is empty")

                due_date = _parse_due_date(values.get("due_date", ""))
                completed = _parse_completed(values.get("completed", ""))
                tags = _parse_tags(values.get("tags", ""))
                recurrence = validate_rule(values.get("recurrence", ""))
                if recurrence and not due_date:
                    raise ValueError("repeating task needs a due date")
                category = values.get("category") or "general"
                priority = (values.get("priority") or "medium").casefold()

                key = _duplicate_key(title, category, due_date)
                if not allow_duplicates and key in seen:
                    result.duplicates += 1
                    continue

                if dry_run:
                    # Validate exactly like a real import, without saving.
                    Task(title=title, priority=priority, tags=tags)
                else:
                    task = manager.create_task(
                        title=title,
                        description=values.get("description", ""),
                        priority=priority,
                        category=category,
                        due_date=due_date,
                        tags=tags,
                        recurrence=recurrence
                    )
                    if completed:
                        manager.complete_task(task.task_id)

                seen.add(key)
                result.imported += 1

            except ValueError as error:
                result.failed += 1
                result.errors.append(f"Line {line}: {error}")

    return result
