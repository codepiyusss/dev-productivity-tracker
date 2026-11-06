import json
from datetime import date

import pytest

from src.analytics import ProductivityAnalytics
from src.database import Database
from src.models.task import Task
from src.reports import ProductivityReports

TODAY = date(2026, 11, 10)  # a Tuesday


@pytest.fixture
def database():
    db = Database(":memory:")

    def add(title, created, **kwargs):
        db.add_task(Task(title, created_at=f"{created}T09:00:00", **kwargs))

    add("Overdue high", "2026-10-20", priority="high", category="work",
        due_date="2026-11-01", tags=["work", "urgent"])
    add("Due soon", "2026-11-09", priority="medium", category="work",
        due_date="2026-11-13", tags=["work"])
    add("Far future", "2026-11-09", priority="low", category="home",
        due_date="2027-01-01")
    add("Finished", "2026-11-03", priority="high", category="work",
        completed=True, tags=["work"])
    add("Finished home", "2026-11-04", priority="low", category="home",
        completed=True)
    return db


@pytest.fixture
def analytics(database):
    return ProductivityAnalytics(database)


def test_overdue_uses_given_date(analytics):
    assert [t.title for t in analytics.get_overdue_tasks(TODAY)] == ["Overdue high"]


def test_overdue_ignores_invalid_due_dates():
    db = Database(":memory:")
    db.add_task(Task("Bad date", due_date="not-a-date"))
    db.add_task(Task("Good", due_date="2020-01-01"))

    result = ProductivityAnalytics(db).get_overdue_tasks(TODAY)

    assert [t.title for t in result] == ["Good"]


def test_due_soon_window_is_inclusive_and_sorted(analytics):
    assert [t.title for t in analytics.get_due_soon_tasks(7, TODAY)] == ["Due soon"]
    assert analytics.get_due_soon_tasks(1, TODAY) == []

    # Exactly `days` ahead still counts.
    assert [t.title for t in analytics.get_due_soon_tasks(3, TODAY)] == ["Due soon"]


def test_priority_and_category_completion(analytics):
    priority = analytics.get_priority_completion()
    assert priority["high"] == {"total": 2, "completed": 1, "completion_rate": 50.0}
    assert priority["low"]["completion_rate"] == 50.0
    assert priority["medium"]["completion_rate"] == 0

    category = analytics.get_category_completion()
    assert category["work"]["total"] == 3
    assert category["work"]["completion_rate"] == 33.33


def test_tag_breakdown_counts_each_tag(analytics):
    tags = analytics.get_tag_breakdown()

    assert set(tags) == {"urgent", "work"}
    assert tags["work"] == {"total": 3, "completed": 1, "completion_rate": 33.33}
    assert tags["urgent"]["total"] == 1


def test_tag_breakdown_empty_when_no_tags():
    db = Database(":memory:")
    db.add_task(Task("Plain"))
    assert ProductivityAnalytics(db).get_tag_breakdown() == {}


def test_pending_age_stats(analytics):
    stats = analytics.get_pending_age_stats(TODAY)

    assert stats["count"] == 3
    assert stats["oldest_days"] == 21
    assert stats["oldest_task"] == "Overdue high"
    assert stats["average_days"] == 7.7


def test_pending_age_stats_when_nothing_pending():
    stats = ProductivityAnalytics(Database(":memory:")).get_pending_age_stats(TODAY)
    assert stats == {
        "count": 0, "oldest_days": 0, "average_days": 0, "oldest_task": None
    }


def test_weekday_distribution_has_all_days(analytics):
    weekdays = analytics.get_weekday_distribution()

    assert list(weekdays)[0] == "Monday"
    assert len(weekdays) == 7
    assert weekdays["Monday"] == {"created": 2, "completed": 0}  # 2026-11-09
    assert sum(d["created"] for d in weekdays.values()) == 5


def test_recent_trend_is_oldest_first(analytics):
    trend = analytics.get_recent_trend(days=3, today=TODAY)

    assert [d["date"] for d in trend] == ["2026-11-08", "2026-11-09", "2026-11-10"]
    assert trend[1]["created"] == 2


def test_insights_mention_key_facts(analytics):
    text = " ".join(analytics.get_insights(TODAY))

    assert "1 task(s) are overdue" in text
    assert "due in the next 7 days" in text
    assert "21 days" in text
    assert "Best completion rate" in text


def test_insights_for_empty_and_finished_lists():
    empty = ProductivityAnalytics(Database(":memory:"))
    assert "No tasks yet" in empty.get_insights()[0]

    db = Database(":memory:")
    db.add_task(Task("Done", completed=True))
    assert any("All tasks are completed" in i
               for i in ProductivityAnalytics(db).get_insights())


def test_detailed_stats_is_json_serializable(analytics):
    stats = analytics.get_detailed_stats(TODAY)

    assert set(stats) == {
        "overview", "priority_completion", "category_completion", "tags",
        "overdue", "due_soon", "pending_age", "weekday_distribution",
        "insights",
    }
    assert json.loads(json.dumps(stats))["overdue"][0]["title"] == "Overdue high"


def test_report_includes_new_sections(database):
    report = ProductivityReports(database).generate_text_report()

    assert "COMPLETION BY PRIORITY" in report
    assert "TAG BREAKDOWN" in report
    assert "#work: 1/3 (33.33%)" in report
    assert "INSIGHTS" in report
    # Original sections are untouched.
    assert "PRODUCTIVITY REPORT" in report
    assert "CATEGORY BREAKDOWN" in report
