import re
from datetime import datetime
from typing import Optional

PREFIX = "productivity-"
EXTENSION = ".db"
TIME_FORMAT = "%Y%m%d-%H%M%S"
MAX_LABEL_LENGTH = 30

_NAME_PATTERN = re.compile(
    r"^productivity-(\d{8}-\d{6})(?:-([a-z0-9-]+))?\.db$"
)


def clean_label(label: Optional[str]) -> Optional[str]:
    """Make a label safe for use in a file name, or None if nothing is left."""
    if not label:
        return None

    cleaned = re.sub(r"[^a-z0-9]+", "-", str(label).casefold()).strip("-")
    cleaned = cleaned[:MAX_LABEL_LENGTH].strip("-")

    return cleaned or None


def backup_filename(now: Optional[datetime] = None, label: Optional[str] = None) -> str:
    """File name such as 'productivity-20261110-153000-before-import.db'."""
    name = PREFIX + (now or datetime.now()).strftime(TIME_FORMAT)
    label = clean_label(label)

    if label:
        name += f"-{label}"

    return name + EXTENSION


def parse_backup_name(name: str):
    """Return (created: datetime, label or None) for a backup file name.

    Returns None for any file that was not named by `backup_filename`.
    """
    match = _NAME_PATTERN.match(name)

    if not match:
        return None

    try:
        created = datetime.strptime(match.group(1), TIME_FORMAT)
    except ValueError:
        return None

    return created, match.group(2)
