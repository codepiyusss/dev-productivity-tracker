import pytest

from src.database import Database
from src.tasks import TaskManager


@pytest.fixture
def manager():
    manager = TaskManager(Database(":memory:"))
    manager.create_task("A", tags=["bug", "urgent"])
    manager.create_task("B", tags=["bug"])
    manager.create_task("C", tags=["fix"])
    return manager


def test_rename_changes_the_tag_on_every_task(manager):
    changed = manager.rename_tag("bug", "defect")

    assert changed == 2
    assert manager.get_all_tags() == {"defect": 2, "fix": 1, "urgent": 1}


def test_names_are_normalized(manager):
    assert manager.rename_tag("  #BUG ", "Defect") == 2
    assert "defect" in manager.get_all_tags()


def test_rename_to_an_existing_tag_is_refused(manager):
    with pytest.raises(ValueError, match="already exists. Use merge"):
        manager.rename_tag("bug", "fix")

    assert manager.get_all_tags()["bug"] == 2


def test_rename_errors(manager):
    with pytest.raises(ValueError, match="same as the old"):
        manager.rename_tag("bug", "BUG")
    with pytest.raises(ValueError, match="'ghost' not found"):
        manager.rename_tag("ghost", "x")
    with pytest.raises(ValueError, match="empty"):
        manager.rename_tag("bug", "  ")


def test_merge_into_existing_or_new_tag(manager):
    assert manager.merge_tags("fix", "bug") == 1
    assert manager.get_all_tags() == {"bug": 3, "urgent": 1}

    assert manager.merge_tags("urgent", "important") == 1
    assert "important" in manager.get_all_tags() and "urgent" not in manager.get_all_tags()


def test_merge_errors(manager):
    with pytest.raises(ValueError, match="two different tags"):
        manager.merge_tags("bug", "#Bug")
    with pytest.raises(ValueError, match="'ghost' not found"):
        manager.merge_tags("ghost", "bug")


def test_delete_tag(manager):
    assert manager.delete_tag("bug") == 2
    assert "bug" not in manager.get_all_tags()
    assert manager.get_task(1).tags == ["urgent"]


def test_delete_unknown_tag_is_an_error(manager):
    with pytest.raises(ValueError, match="'ghost' not found"):
        manager.delete_tag("ghost")
