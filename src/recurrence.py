import calendar
from datetime import date, timedelta
from typing import Optional

RULES = ("daily", "weekly", "monthly")


def validate_rule(rule: Optional[str]) -> Optional[str]:
    """Return a clean rule name, or None for no repeat. Raises ValueError."""
    if rule is None or not str(rule).strip():
        return None

    cleaned = str(rule).strip().casefold()

    if cleaned not in RULES:
        raise ValueError(f"Repeat must be one of: {', '.join(RULES)}.")

    return cleaned


def _add_months(day: date, months: int) -> date:
    """Move a date forward by whole months, clamping to the month's length."""
    index = day.month - 1 + months
    year = day.year + index // 12
    month = index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]

    return date(year, month, min(day.day, last_day))


def _step(day: date, rule: str) -> date:
    if rule == "daily":
        return day + timedelta(days=1)

    if rule == "weekly":
        return day + timedelta(days=7)

    return _add_months(day, 1)


def next_due_date(due: date, rule: str, today: Optional[date] = None) -> date:
    """The next due date after completing a recurring task.

    The schedule moves forward from the old due date, one step at a time,
    until it lands after today. Finishing early therefore gives the next
    regular date, and finishing very late does not leave a pile of
    already-overdue copies.

    Monthly repeats clamp to the end of short months (Jan 31 -> Feb 28),
    and the shorter day carries forward from then on.
    """
    rule = validate_rule(rule)

    if rule is None:
        raise ValueError("A repeat rule is required.")

    today = today or date.today()
    following = _step(due, rule)

    while following <= today:
        following = _step(following, rule)

    return following
