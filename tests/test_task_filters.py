import pytest

from src.database import Database
from src.tasks import TaskManager
from src.task_filters import filter_tasks


@pytest.fixture
def tasks():
    manager = TaskManager(Database(":memory:"))

    first = manager.create_task(
        "Study Python", description="Learn functions",
        priority="high", category="learning"
    )
    second = manager.create_task(
        "Build website", priority="medium", category="development"
    )
    third = manager.create_task(
        "Read Python documentation",
        priority="low", category="learning"
    )

    manager.complete_task(second.task_id)

    return manager.get_all_tasks()


def test_search_by_title(tasks):
    result = filter_tasks(tasks, keyword="python")
    assert len(result) == 2


def test_filter_by_priority(tasks):
    result = filter_tasks(tasks, priority="high")
    assert len(result) == 1
    assert result[0].title == "Study Python"


def test_filter_by_category(tasks):
    result = filter_tasks(tasks, category="learning")
    assert len(result) == 2


def test_filter_by_status(tasks):
    result = filter_tasks(tasks, status="completed")
    assert len(result) == 1
    assert result[0].title == "Build website"


def test_sort_by_title(tasks):
    result = filter_tasks(tasks, sort_by="title", descending=False)
    assert [task.title for task in result] == sorted(
        task.title for task in tasks
    )


def test_invalid_status(tasks):
    with pytest.raises(ValueError):
        filter_tasks(tasks, status="archived")
