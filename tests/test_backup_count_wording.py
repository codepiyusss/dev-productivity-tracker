from src.backup import format_counts


def counts(**values):
    base = {"tasks": 0, "time_entries": 0, "goals": 0, "journal_entries": 0, "task_dependencies": 0}
    base.update(values)
    return base


def test_singular_forms_for_exactly_one():
    assert format_counts(counts(
        tasks=1, time_entries=1, goals=1, journal_entries=1, task_dependencies=1
    )) == "1 task, 1 time entry, 1 goal, 1 journal entry, 1 dependency"


def test_plural_forms_for_other_numbers():
    assert format_counts(counts(
        tasks=2, time_entries=3, goals=2, journal_entries=12, task_dependencies=5
    )) == "2 tasks, 3 time entries, 2 goals, 12 journal entries, 5 dependencies"


def test_zero_counts_are_left_out_and_empty_is_reported():
    assert format_counts(counts(tasks=4)) == "4 tasks"
    assert format_counts(counts()) == "empty"
