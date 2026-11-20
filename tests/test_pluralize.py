import pytest

from src.utils import pluralize


@pytest.mark.parametrize("count, expected", [
    (0, "0 tasks"), (1, "1 task"), (2, "2 tasks"), (100, "100 tasks"),
])
def test_regular_plural(count, expected):
    assert pluralize(count, "task") == expected


@pytest.mark.parametrize("count, expected", [
    (0, "0 entries"), (1, "1 entry"), (5, "5 entries"),
])
def test_irregular_plural(count, expected):
    assert pluralize(count, "entry", "entries") == expected


def test_negative_numbers_use_the_plural():
    assert pluralize(-1, "task") == "-1 tasks"


def test_works_with_multiword_labels():
    assert pluralize(1, "time entry", "time entries") == "1 time entry"
    assert pluralize(3, "time entry", "time entries") == "3 time entries"
