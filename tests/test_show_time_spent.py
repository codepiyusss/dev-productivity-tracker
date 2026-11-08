from src.main import format_task_details, main
from src.models.task import Task


def task():
    return Task("Write docs", task_id=3, created_at="2026-11-10T09:00:00")


def test_details_omit_time_when_nothing_was_tracked():
    assert "Time spent" not in format_task_details(task())


def test_details_show_tracked_time():
    text = format_task_details(task(), tracked_seconds=5100)

    assert "  Time spent:  1h 25m" in text
    assert "timer running" not in text


def test_details_flag_a_running_timer_even_at_zero_seconds():
    text = format_task_details(task(), tracked_seconds=0, timer_running=True)

    assert "  Time spent:  0s (timer running)" in text


def test_time_line_sits_before_the_description():
    lines = format_task_details(task(), tracked_seconds=60).splitlines()

    assert lines[-1].startswith("  Description:")
    assert lines[-2].startswith("  Time spent:")


def test_show_command_includes_time_for_the_right_task(tmp_path, capsys):
    def run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    run("add", "Write docs")
    run("add", "Other")
    run("timer", "log", "1", "45m")
    capsys.readouterr()

    run("show", "1")
    assert "Time spent:  45m" in capsys.readouterr().out

    run("show", "2")
    assert "Time spent" not in capsys.readouterr().out


def test_show_flags_a_running_timer(tmp_path, capsys):
    def run(*argv):
        return main(["--db", str(tmp_path / "t.db"), *argv])

    run("add", "Write docs")
    run("timer", "start", "1")
    capsys.readouterr()

    run("show", "1")

    assert "(timer running)" in capsys.readouterr().out
