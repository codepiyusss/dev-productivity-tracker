from src.tasks import Task

def test_task_completion():
    task = Task('Learn Python')
    task.mark_completed()
    assert task.completed
