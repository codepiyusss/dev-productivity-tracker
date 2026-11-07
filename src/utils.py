from datetime import datetime

from src.constants import DATE_FORMAT


def clean_text(value):
    return value.strip()


def normalize_tag(tag):
    """Return a clean lowercase tag, or raise ValueError if invalid."""
    cleaned = " ".join(str(tag).strip().lstrip("#").split()).casefold()

    if not cleaned:
        raise ValueError("Tag cannot be empty.")

    if "," in cleaned:
        raise ValueError("Tag cannot contain commas.")

    if len(cleaned) > 30:
        raise ValueError("Tag cannot be longer than 30 characters.")

    return cleaned


def normalize_tags(tags):
    """Normalize an iterable of tags, removing duplicates but keeping order."""
    unique = []

    for tag in tags or []:
        cleaned = normalize_tag(tag)
        if cleaned not in unique:
            unique.append(cleaned)

    return unique


def parse_tag_string(value):
    """Turn 'work, urgent' into ['work', 'urgent']."""
    if not value:
        return []

    return normalize_tags(part for part in value.split(",") if part.strip())


def validate_due_date(value):
    """Return a normalized YYYY-MM-DD string, or None for an empty value.

    Raises ValueError for anything that is not a real calendar date.
    """
    if value is None or not str(value).strip():
        return None

    try:
        return datetime.strptime(str(value).strip(), DATE_FORMAT).date().isoformat()
    except ValueError:
        raise ValueError("Due date must be a real date in YYYY-MM-DD format.")
