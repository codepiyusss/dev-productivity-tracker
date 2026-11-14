import pytest

from src.database import Database
from src.search import search_tasks, split_terms
from src.tasks import TaskManager


@pytest.fixture
def tasks():
    manager = TaskManager(Database(":memory:"))
    manager.create_task("Write Python docs", description="Explain the CLI", category="work", tags=["docs"])
    manager.create_task("Fix login bug", description="Python traceback on login", category="work", tags=["bugfix"])
    manager.create_task("Buy milk", category="home")
    manager.create_task("Read book", description="Learn python basics", category="learning", tags=["python"])
    return manager.get_all_tasks()


def titles(results):
    return [r["task"].title for r in results]


def test_split_terms_lowercases_and_splits():
    assert split_terms("  Python   DOCS ") == ["python", "docs"]


@pytest.mark.parametrize("query", ["", "   ", None])
def test_empty_query_is_rejected(query):
    with pytest.raises(ValueError, match="something to search for"):
        split_terms(query)


def test_matches_title_description_tags_and_category(tasks):
    assert set(titles(search_tasks(tasks, "python"))) == {
        "Write Python docs", "Fix login bug", "Read book",
    }
    assert titles(search_tasks(tasks, "home")) == ["Buy milk"]
    assert titles(search_tasks(tasks, "bugfix")) == ["Fix login bug"]


def test_search_is_case_insensitive_and_matches_inside_words(tasks):
    assert titles(search_tasks(tasks, "PYTH")) == titles(search_tasks(tasks, "python"))


def test_every_word_must_match_somewhere(tasks):
    assert titles(search_tasks(tasks, "python login")) == ["Fix login bug"]
    assert search_tasks(tasks, "python milk") == []


def test_a_title_match_outranks_tags_and_description_combined(tasks):
    results = search_tasks(tasks, "python")

    assert results[0]["task"].title == "Write Python docs"   # title + nothing else
    assert results[0]["score"] > results[-1]["score"]


def test_results_report_which_fields_matched(tasks):
    top = search_tasks(tasks, "python")
    by_title = {r["task"].title: r for r in top}

    assert by_title["Write Python docs"]["fields"] == ["title"]
    assert by_title["Fix login bug"]["fields"] == ["description"]
    assert by_title["Read book"]["fields"] == ["tags", "description"]


def test_ties_prefer_the_newest_task():
    manager = TaskManager(Database(":memory:"))
    manager.create_task("Alpha note")
    manager.create_task("Beta note")

    assert titles(search_tasks(manager.get_all_tasks(), "note")) == ["Beta note", "Alpha note"]


def test_no_match_gives_an_empty_list(tasks):
    assert search_tasks(tasks, "zebra") == []


def test_completed_tasks_are_searched_too():
    manager = TaskManager(Database(":memory:"))
    task = manager.create_task("Old release notes")
    manager.complete_task(task.task_id)

    assert titles(search_tasks(manager.get_all_tasks(), "release")) == ["Old release notes"]
