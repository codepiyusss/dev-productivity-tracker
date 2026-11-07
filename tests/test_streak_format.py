from src.streaks import format_streak_summary


def summary(**overrides):
    base = {
        "current": 3, "active_today": True, "last_active": "2026-11-12",
        "at_risk": False, "longest": 7,
        "longest_start": "2026-10-01", "longest_end": "2026-10-07",
        "goal_streak": None, "daily_target": None, "total_active_days": 12,
        "recent": [
            {"date": f"2026-11-{day:02d}", "completed": count}
            for day, count in zip(range(8, 13), [0, 1, 2, 0, 1])
        ],
    }
    base.update(overrides)
    return base


def test_full_summary_text():
    text = format_streak_summary(summary())

    assert text.splitlines() == [
        "Current streak: 3 days (completed a task today)",
        "Longest streak: 7 days (2026-10-01 to 2026-10-07)",
        "Active days: 12",
        "Last 5 days: [-##-#] (oldest to today)",
    ]


def test_at_risk_streak_prompts_to_continue():
    text = format_streak_summary(summary(current=2, active_today=False, at_risk=True))

    assert "Current streak: 2 days (complete a task today to keep it going)" in text


def test_singular_day_wording():
    text = format_streak_summary(summary(current=1, longest=1))

    assert "Current streak: 1 day (" in text
    assert "Longest streak: 1 day (" in text


def test_no_streak_yet():
    text = format_streak_summary(summary(
        current=0, active_today=False, longest=0, longest_start=None,
        longest_end=None, total_active_days=0,
        recent=[{"date": "2026-11-12", "completed": 0}],
    ))

    assert "Current streak: 0 days (complete a task to start one)" in text
    assert "Longest streak: 0 days" in text
    assert "[-]" in text


def test_goal_streak_line_only_when_goal_exists():
    assert "Goal streak" not in format_streak_summary(summary())

    text = format_streak_summary(summary(goal_streak=4, daily_target=3))
    assert "Goal streak: 4 days (daily target: 3)" in text
