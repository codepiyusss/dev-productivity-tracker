from src.backup import create_backup, describe_database, format_counts, restore_backup
from src.database import Database
from src.dependencies import DependencyManager
from src.tasks import TaskManager


def build(path):
    database = Database(path)
    manager = TaskManager(database)
    for title in ("A", "B", "C"):
        manager.create_task(title)
    dependencies = DependencyManager(database)
    dependencies.add(2, 1)
    dependencies.add(3, 2)
    return database


def test_dependencies_are_counted_in_a_backup(tmp_path):
    db = str(tmp_path / "t.db")
    build(db)

    info = create_backup(db, tmp_path / "b")

    assert info["counts"]["task_dependencies"] == 2
    assert "2 dependencies" in format_counts(info["counts"])


def test_restore_brings_dependencies_back(tmp_path):
    db = str(tmp_path / "t.db")
    database = build(db)
    backup = create_backup(db, tmp_path / "b")["path"]
    database.remove_dependency(2, 1)
    database.remove_dependency(3, 2)
    assert Database(db).get_all_dependencies() == []

    restore_backup(backup, db)

    assert Database(db).get_all_dependencies() == [(2, 1), (3, 2)]


def test_an_old_backup_without_the_table_counts_zero(tmp_path):
    import sqlite3
    db = str(tmp_path / "t.db")
    build(db)
    connection = sqlite3.connect(db)
    with connection:
        connection.execute("DROP TABLE task_dependencies")
    connection.close()

    assert describe_database(db)["counts"]["task_dependencies"] == 0
