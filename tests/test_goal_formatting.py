from src.goals import format_progress


def progress(**overrides):
    base = {
        "period": "daily", "target": 3, "completed": 1, "remaining": 2,
        "percent": 33.3, "met": False,
    }
    base.update(overrides)
    return base


def test_partial_progress_line():
    assert format_progress(progress()) == (
        "Daily goal: [###-------] 1/3 (33.3%) - 2 to go"
    )


def test_met_goal_line():
    line = format_progress(progress(
        period="weekly", target=2, completed=3, remaining=0,
        percent=100, met=True,
    ))

    assert line == "Weekly goal: [##########] 3/2 (100%) - goal met!"


def test_empty_bar_when_nothing_done():
    line = format_progress(progress(completed=0, remaining=3, percent=0))

    assert "[----------]" in line
