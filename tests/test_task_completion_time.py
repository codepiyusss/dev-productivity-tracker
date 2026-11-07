from datetime import datetime

from src.models.task import Task


def test_new_task_has_no_completion_time():
    task = Task("Write docs")

    assert task.completed is False
    assert task.completed_at is None


def test_mark_completed_records_timestamp():
    task = Task("Write docs")

    task.mark_completed()

    assert task.completed is True
    assert datetime.fromisoformat(task.completed_at)


def test_completing_twice_keeps_first_timestamp():
    task = Task("Write docs")
    task.mark_completed()
    first = task.completed_at
    task.completed_at = "2026-01-01T08:00:00"

    task.mark_completed()

    assert task.completed_at == "2026-01-01T08:00:00"
    assert first != "2026-01-01T08:00:00"


def test_mark_pending_clears_timestamp():
    task = Task("Write docs")
    task.mark_completed()

    task.mark_pending()

    assert task.completed is False
    assert task.completed_at is None


def test_to_dict_includes_completed_at():
    task = Task("Write docs", completed_at="2026-11-10T09:30:00")

    assert task.to_dict()["completed_at"] == "2026-11-10T09:30:00"
    assert Task.from_dict(task.to_dict()).completed_at == "2026-11-10T09:30:00"
