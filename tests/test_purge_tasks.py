import pytest

from src.database import Database
from src.dependencies import DependencyManager
from src.housekeeping import describe_purge, purge_tasks
from src.tasks import TaskManager
from src.timetracking import TimeTracker


@pytest.fixture
def setup():
    database = Database(":memory:")
    manager = TaskManager(database)
    old = manager.create_task("Old", tags=["x"])
    keep = manager.create_task("Keep")
    blocked = manager.create_task("Waits for old")
    tracker = TimeTracker(database)
    tracker.log_manual(old.task_id, 600)
    tracker.log_manual(old.task_id, 300)
    tracker.log_manual(keep.task_id, 900)
    DependencyManager(database).add(blocked.task_id, old.task_id)
    return database, old, keep, blocked


def test_describe_counts_everything_that_would_go(setup):
    database, old, _, _ = setup

    assert describe_purge(database, [old]) == {
        "tasks": 1, "time_entries": 2, "dependency_links": 1,
    }


def test_describe_does_not_delete_anything(setup):
    database, old, _, _ = setup

    describe_purge(database, [old])

    assert len(database.get_all_tasks()) == 3
    assert len(database.get_time_entries()) == 3


def test_purge_deletes_tasks_and_attached_data(setup):
    database, old, keep, blocked = setup

    summary = purge_tasks(database, [old])

    assert summary == {"tasks": 1, "time_entries": 2, "dependency_links": 1}
    assert sorted(t.title for t in database.get_all_tasks()) == ["Keep", "Waits for old"]
    assert [e["task_id"] for e in database.get_time_entries()] == [keep.task_id]
    assert database.get_all_dependencies() == []
    assert database.get_tag_counts() == {}


def test_other_tasks_are_untouched(setup):
    database, old, keep, blocked = setup

    purge_tasks(database, [old])

    assert database.get_task(keep.task_id).title == "Keep"
    assert database.get_task(blocked.task_id).title == "Waits for old"


def test_purging_nothing_is_a_no_op(setup):
    database, _, _, _ = setup

    assert purge_tasks(database, []) == {"tasks": 0, "time_entries": 0, "dependency_links": 0}
    assert len(database.get_all_tasks()) == 3


def test_purging_several_tasks_counts_shared_links_once(setup):
    database, old, _, blocked = setup

    summary = purge_tasks(database, [old, blocked])

    assert summary["tasks"] == 2
    assert summary["dependency_links"] == 1
    assert [t.title for t in database.get_all_tasks()] == ["Keep"]
