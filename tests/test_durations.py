import pytest

from src.utils import format_duration, parse_duration


@pytest.mark.parametrize("seconds, expected", [
    (0, "0s"), (45, "45s"), (59, "59s"), (60, "1m"), (125, "2m"),
    (2700, "45m"), (3600, "1h"), (3660, "1h 1m"), (5100, "1h 25m"),
    (7200, "2h"), (90000, "25h"), (-5, "0s"),
])
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


@pytest.mark.parametrize("text, expected", [
    ("90", 5400), ("45", 2700), ("45m", 2700), ("1h", 3600),
    ("1h30m", 5400), ("1h 30m", 5400), ("1.5h", 5400), ("1:30", 5400),
    ("0:45", 2700), ("2H", 7200), ("0.5", 30), ("24h", 86400),
])
def test_parse_duration_accepts_common_forms(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text", [
    "", "   ", "abc", "1x", "h", "1:75", "-5", "0", "0m", "25h", "1h2", "1,5h",
])
def test_parse_duration_rejects_bad_input(text):
    with pytest.raises(ValueError):
        parse_duration(text)


def test_error_message_suggests_valid_forms():
    with pytest.raises(ValueError, match="1h30m"):
        parse_duration("lots")


def test_round_trip_for_whole_minutes():
    assert parse_duration("1h25m") == 5100
    assert format_duration(parse_duration("1h25m")) == "1h 25m"
