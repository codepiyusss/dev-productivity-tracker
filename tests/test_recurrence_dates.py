from datetime import date

import pytest

from src.recurrence import next_due_date, validate_rule

TODAY = date(2026, 11, 10)


@pytest.mark.parametrize("value, expected", [
    ("daily", "daily"), (" Weekly ", "weekly"), ("MONTHLY", "monthly"),
    (None, None), ("", None), ("   ", None),
])
def test_validate_rule(value, expected):
    assert validate_rule(value) == expected


@pytest.mark.parametrize("value", ["yearly", "hourly", "every day", "1"])
def test_validate_rule_rejects_unknown_values(value):
    with pytest.raises(ValueError, match="daily, weekly, monthly"):
        validate_rule(value)


def test_daily_weekly_monthly_from_a_future_due_date():
    due = date(2026, 11, 20)

    assert next_due_date(due, "daily", TODAY) == date(2026, 11, 21)
    assert next_due_date(due, "weekly", TODAY) == date(2026, 11, 27)
    assert next_due_date(due, "monthly", TODAY) == date(2026, 12, 20)


def test_completing_on_the_due_day_moves_to_the_next_date():
    assert next_due_date(TODAY, "daily", TODAY) == date(2026, 11, 11)
    assert next_due_date(TODAY, "weekly", TODAY) == date(2026, 11, 17)


def test_late_completion_skips_dates_already_in_the_past():
    due = date(2026, 11, 1)  # nine days late

    assert next_due_date(due, "daily", TODAY) == date(2026, 11, 11)
    assert next_due_date(due, "weekly", TODAY) == date(2026, 11, 15)
    assert next_due_date(due, "monthly", TODAY) == date(2026, 12, 1)


def test_weekly_keeps_the_same_weekday_when_late():
    due = date(2026, 10, 5)  # a Monday, five weeks ago

    result = next_due_date(due, "weekly", TODAY)

    assert result == date(2026, 11, 16)
    assert result.weekday() == due.weekday()


def test_monthly_clamps_to_the_end_of_short_months():
    assert next_due_date(date(2026, 1, 31), "monthly", date(2026, 1, 31)) == date(2026, 2, 28)
    assert next_due_date(date(2028, 1, 31), "monthly", date(2028, 1, 31)) == date(2028, 2, 29)
    assert next_due_date(date(2026, 3, 31), "monthly", date(2026, 3, 31)) == date(2026, 4, 30)


def test_monthly_rolls_over_the_year_end():
    assert next_due_date(date(2026, 12, 15), "monthly", date(2026, 12, 1)) == date(2027, 1, 15)


def test_result_is_always_after_today():
    for rule in ("daily", "weekly", "monthly"):
        for offset in range(-90, 90, 7):
            due = date.fromordinal(TODAY.toordinal() + offset)
            assert next_due_date(due, rule, TODAY) > TODAY


def test_rule_is_required():
    with pytest.raises(ValueError):
        next_due_date(TODAY, "", TODAY)


def test_defaults_to_the_real_today():
    assert next_due_date(date(2000, 1, 1), "daily") > date.today()
