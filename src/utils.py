import re
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


MAX_MANUAL_SECONDS = 24 * 3600


def format_duration(seconds):
    """Readable duration: 30s, 45m, 2h, 1h 25m. Negative values show as 0s."""
    seconds = max(int(seconds), 0)

    if seconds < 60:
        return f"{seconds}s"

    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60

    if hours == 0:
        return f"{minutes}m"

    return f"{hours}h" if minutes == 0 else f"{hours}h {minutes}m"


def parse_duration(text):
    """Turn '90', '45m', '1h30m', '1.5h' or '1:30' into seconds.

    A bare number means minutes. Raises ValueError for anything that is
    not a positive duration of at most 24 hours.
    """
    value = str(text).strip().casefold().replace(" ", "")

    if not value:
        raise ValueError("Duration cannot be empty.")

    seconds = None

    if re.fullmatch(r"\d+:\d{1,2}", value):
        hours, minutes = value.split(":")
        if int(minutes) < 60:
            seconds = int(hours) * 3600 + int(minutes) * 60
    elif re.fullmatch(r"\d+(\.\d+)?", value):
        seconds = round(float(value) * 60)
    else:
        match = re.fullmatch(r"(?:(\d+(?:\.\d+)?)h)?(?:(\d+)m)?", value)
        if match and (match.group(1) or match.group(2)):
            seconds = round(
                float(match.group(1) or 0) * 3600 + int(match.group(2) or 0) * 60
            )

    if seconds is None:
        raise ValueError(
            f"Could not read duration '{text}'. Try 45, 45m, 1h30m or 1:30."
        )

    if seconds <= 0:
        raise ValueError("Duration must be greater than zero.")

    if seconds > MAX_MANUAL_SECONDS:
        raise ValueError("Duration cannot be longer than 24 hours.")

    return seconds
