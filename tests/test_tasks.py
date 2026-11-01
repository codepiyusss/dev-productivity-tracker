from src.tasks import Task

def test_task_completion():
    task = Task('Learn Python')
    task.complete()
    assert task.completed
