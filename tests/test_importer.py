import pytest

from src.database import Database
from src.exporter import export_tasks_csv
from src.importer import import_tasks_csv
from src.tasks import TaskManager


@pytest.fixture
def manager():
    return TaskManager(Database(":memory:"))


def write_csv(tmp_path, text, name="in.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8", newline="")
    return str(path)


def test_import_basic_rows(manager, tmp_path):
    path = write_csv(tmp_path, (
        "title,priority,category,due_date,completed,tags\n"
        "Write docs,high,work,2026-12-01,no,docs;writing\n"
        "Buy milk,low,home,,yes,\n"
    ))

    result = import_tasks_csv(path, manager)

    assert (result.imported, result.failed, result.duplicates) == (2, 0, 0)
    docs = next(t for t in manager.get_all_tasks() if t.title == "Write docs")
    assert docs.priority == "high"
    assert docs.due_date == "2026-12-01"
    assert docs.tags == ["docs", "writing"]
    milk = next(t for t in manager.get_all_tasks() if t.title == "Buy milk")
    assert milk.completed is True


def test_import_uses_defaults_for_missing_columns(manager, tmp_path):
    path = write_csv(tmp_path, "title\nOnly a title\n")

    import_tasks_csv(path, manager)

    task = manager.get_all_tasks()[0]
    assert (task.priority, task.category, task.tags) == ("medium", "general", [])


def test_import_handles_bom_headers_case_and_comma_tags(manager, tmp_path):
    path = write_csv(
        tmp_path,
        '\ufeffTitle,Due Date,Tags\n"Plan, review",2026-12-05,"a, b"\n'
    )

    result = import_tasks_csv(path, manager)

    assert result.imported == 1
    task = manager.get_all_tasks()[0]
    assert task.title == "Plan, review"
    assert task.due_date == "2026-12-05"
    assert task.tags == ["a", "b"]


def test_bad_rows_are_skipped_with_line_numbers(manager, tmp_path):
    path = write_csv(tmp_path, (
        "title,priority,due_date,completed\n"
        "Good,high,2026-12-01,no\n"
        ",low,,no\n"
        "Bad priority,urgent,,no\n"
        "Bad date,low,01/12/2026,no\n"
        "Bad status,low,,maybe\n"
        "Also good,low,,no\n"
    ))

    result = import_tasks_csv(path, manager)

    assert result.imported == 2
    assert result.failed == 4
    assert [e.split(":")[0] for e in result.errors] == [
        "Line 3", "Line 4", "Line 5", "Line 6"
    ]
    assert len(manager.get_all_tasks()) == 2


def test_duplicates_are_skipped_by_default(manager, tmp_path):
    manager.create_task("Write docs", category="work")
    path = write_csv(tmp_path, (
        "title,category\n"
        "write docs,WORK\n"
        "New task,work\n"
        "New task,work\n"
    ))

    result = import_tasks_csv(path, manager)

    assert (result.imported, result.duplicates) == (1, 2)
    assert len(manager.get_all_tasks()) == 2


def test_allow_duplicates_imports_everything(manager, tmp_path):
    manager.create_task("Write docs")
    path = write_csv(tmp_path, "title\nWrite docs\n")

    result = import_tasks_csv(path, manager, allow_duplicates=True)

    assert result.imported == 1
    assert len(manager.get_all_tasks()) == 2


def test_dry_run_saves_nothing_but_reports(manager, tmp_path):
    path = write_csv(tmp_path, "title,priority\nGood,high\nBad,urgent\n")

    result = import_tasks_csv(path, manager, dry_run=True)

    assert (result.imported, result.failed) == (1, 1)
    assert manager.get_all_tasks() == []


def test_missing_file_and_missing_title_column(manager, tmp_path):
    with pytest.raises(ValueError, match="not found"):
        import_tasks_csv(str(tmp_path / "nope.csv"), manager)

    with pytest.raises(ValueError, match="title"):
        import_tasks_csv(write_csv(tmp_path, "name\nx\n", "a.csv"), manager)

    with pytest.raises(ValueError, match="empty"):
        import_tasks_csv(write_csv(tmp_path, "", "b.csv"), manager)


def test_export_then_import_round_trip(tmp_path):
    source = TaskManager(Database(":memory:"))
    source.create_task(
        "Ship, release", description='Say "hi"\nline two', priority="high",
        category="work", due_date="2026-12-01", tags=["work", "urgent"]
    )
    done = source.create_task("Café ☕")
    source.complete_task(done.task_id)
    path = export_tasks_csv(source.get_all_tasks(), str(tmp_path / "x.csv"))

    target = TaskManager(Database(":memory:"))
    result = import_tasks_csv(path, target)

    assert (result.imported, result.failed) == (2, 0)
    by_title = {t.title: t for t in target.get_all_tasks()}
    release = by_title["Ship, release"]
    assert release.description == 'Say "hi"\nline two'
    assert (release.priority, release.category) == ("high", "work")
    assert release.tags == ["work", "urgent"]
    assert by_title["Café ☕"].completed is True

    # Importing the same file again adds nothing.
    again = import_tasks_csv(path, target)
    assert (again.imported, again.duplicates) == (0, 2)
