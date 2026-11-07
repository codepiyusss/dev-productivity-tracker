import sqlite3

import pytest

from src.database import Database


@pytest.fixture
def database():
    return Database(":memory:")


def test_no_goal_by_default(database):
    assert database.get_goal("daily") is None
    assert database.get_goals() == {}


def test_set_and_get_goal(database):
    database.set_goal("daily", 3)

    assert database.get_goal("daily") == 3
    assert database.get_goals() == {"daily": 3}


def test_setting_goal_again_replaces_it(database):
    database.set_goal("daily", 3)
    database.set_goal("daily", 5)

    assert database.get_goal("daily") == 5
    assert len(database.get_goals()) == 1


def test_daily_and_weekly_goals_are_independent(database):
    database.set_goal("weekly", 15)
    database.set_goal("daily", 3)

    assert database.get_goals() == {"daily": 3, "weekly": 15}


def test_clear_goal(database):
    database.set_goal("daily", 3)

    assert database.clear_goal("daily") is True
    assert database.clear_goal("daily") is False
    assert database.get_goal("daily") is None


def test_database_rejects_non_positive_target(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.set_goal("daily", 0)


def test_goals_persist_across_connections(tmp_path):
    path = str(tmp_path / "goals.db")
    Database(path).set_goal("weekly", 10)

    assert Database(path).get_goal("weekly") == 10
