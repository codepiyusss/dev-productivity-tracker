import argparse
import json
import sqlite3
import sys
from pathlib import Path

from src.backup import (
    backups_to_prune, create_backup, default_backup_dir, format_backup_entry, format_counts,
    describe_database, format_size, list_backups, prune_backups, restore_backup,
    verify_database
)
from src.database import Database
from src.tasks import TaskManager
from src.analytics import ProductivityAnalytics
from src.recurrence import RULES
from src.reports import ProductivityReports
from src.streaks import StreakTracker, format_streak_summary
from src.task_filters import filter_tasks
from src.journal import ProductivityJournal
from src.exporter import export_tasks
from src.goals import PERIODS, GoalTracker, format_progress
from src.importer import import_tasks_csv
from src.timetracking import (
    STALE_AFTER_SECONDS, TimeTracker, format_time_summary
)
from src.utils import (
    format_duration, parse_duration, parse_tag_string, validate_due_date
)
from datetime import date, timedelta


def positive_int(value):
    """argparse type: a whole number of at least 1."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a whole number")

    if number < 1:
        raise argparse.ArgumentTypeError(f"{number} must be at least 1")

    return number


def non_negative_int(value):
    """argparse type: a whole number of at least 0."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a whole number")

    if number < 0:
        raise argparse.ArgumentTypeError(f"{number} cannot be negative")

    return number


def duration_seconds(value):
    """argparse type: '45', '45m', '1h30m' or '1:30', returned as seconds."""
    try:
        return parse_duration(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error))


def valid_date(value):
    """argparse type: a real date, returned as YYYY-MM-DD."""
    try:
        return validate_due_date(value) or ""
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid date '{value}' (use YYYY-MM-DD)"
        )


EXAMPLES = """examples:
  python -m src.main add "Write docs" --priority high --due-date 2026-12-01 --tags work
  python -m src.main list --status pending --sort due_date --ascending
  python -m src.main complete 3
  python -m src.main goal set daily 3
  python -m src.main streak
  python -m src.main --db other.db stats --detailed

Run "python -m src.main <command> --help" for details on one command."""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Dev Productivity Tracker",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        help="Use a different database file (must come before the command)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    # Task commands
    add = commands.add_parser("add", help="Create a task")
    add.add_argument("title")
    add.add_argument("--priority", choices=["low", "medium", "high"], default="medium")
    add.add_argument("--category", default="general")
    add.add_argument("--description", default="")
    add.add_argument("--due-date", type=valid_date, help="YYYY-MM-DD")
    add.add_argument("--tags", help="Comma-separated tags, e.g. work,urgent")
    add.add_argument(
        "--repeat", choices=RULES,
        help="Repeat the task after it is completed (needs --due-date)"
    )

    list_parser = commands.add_parser("list", help="List and filter tasks")
    list_parser.add_argument("--search")
    list_parser.add_argument("--priority", choices=["low", "medium", "high"])
    list_parser.add_argument("--category")
    list_parser.add_argument("--status", choices=["pending", "completed"])
    list_parser.add_argument(
        "--tag",
        action="append",
        help="Only show tasks with this tag (repeat to require several)"
    )
    list_parser.add_argument(
        "--sort",
        choices=["title", "priority", "category", "created_at", "due_date"],
        default="created_at"
    )
    list_parser.add_argument("--ascending", action="store_true")

    export = commands.add_parser("export", help="Export tasks to CSV or JSON")
    export.add_argument("--format", choices=["csv", "json"], default="csv")
    export.add_argument("--output", help="Output file (default: tasks_export.<format>)")
    export.add_argument("--status", choices=["pending", "completed"])
    export.add_argument("--priority", choices=["low", "medium", "high"])
    export.add_argument("--category")
    export.add_argument("--tag", action="append", help="Only export tasks with this tag")
    export.add_argument(
        "--include-time", action="store_true",
        help="Add a time_spent_seconds column from the time tracker"
    )

    import_parser = commands.add_parser("import", help="Import tasks from a CSV file")
    import_parser.add_argument("csv_file")
    import_parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate the file and show results without saving anything"
    )
    import_parser.add_argument(
        "--allow-duplicates", action="store_true",
        help="Import tasks even if a matching task already exists"
    )

    # Tag commands
    tag = commands.add_parser("tag", help="Manage task tags")
    tag_commands = tag.add_subparsers(dest="tag_command", required=True)

    tag_add = tag_commands.add_parser("add", help="Add tags to a task")
    tag_add.add_argument("task_id", type=positive_int)
    tag_add.add_argument("tags", help="Comma-separated tags")

    tag_remove = tag_commands.add_parser("remove", help="Remove tags from a task")
    tag_remove.add_argument("task_id", type=positive_int)
    tag_remove.add_argument("tags", help="Comma-separated tags")

    tag_commands.add_parser("list", help="List all tags with task counts")

    goal = commands.add_parser("goal", help="Manage daily and weekly goals")
    goal_commands = goal.add_subparsers(dest="goal_command", required=True)

    goal_set = goal_commands.add_parser("set", help="Set a completion target")
    goal_set.add_argument("period", choices=PERIODS)
    goal_set.add_argument("target", type=int, help="Tasks to complete")

    goal_commands.add_parser("show", help="Show progress toward your goals")

    goal_clear = goal_commands.add_parser("clear", help="Remove a goal")
    goal_clear.add_argument("period", choices=PERIODS)

    streak = commands.add_parser("streak", help="Show your completion streaks")
    streak.add_argument(
        "--days", type=int, default=14,
        help="Days of recent activity to display (default: 14)"
    )
    streak.add_argument(
        "--json", action="store_true", help="Print the streak data as JSON"
    )

    timer = commands.add_parser("timer", help="Track time spent on tasks")
    timer_commands = timer.add_subparsers(dest="timer_command", required=True)

    timer_start = timer_commands.add_parser("start", help="Start a timer on a task")
    timer_start.add_argument("task_id", type=positive_int)

    timer_commands.add_parser("stop", help="Stop the running timer")

    timer_log = timer_commands.add_parser(
        "log", help="Record time you did not track with a timer"
    )
    timer_log.add_argument("task_id", type=positive_int)
    timer_log.add_argument(
        "duration", type=duration_seconds,
        help="e.g. 45, 45m, 1h30m or 1:30 (a bare number means minutes)"
    )
    timer_log.add_argument(
        "--date", dest="log_date", type=valid_date,
        help="Day the work happened, YYYY-MM-DD (default: today)"
    )
    timer_commands.add_parser("status", help="Show the running timer")

    timer_delete = timer_commands.add_parser(
        "delete", help="Delete a time entry (IDs are shown by 'timer list')"
    )
    timer_delete.add_argument("entry_id", type=positive_int)
    timer_delete.add_argument(
        "-y", "--yes", action="store_true", help="Delete without asking"
    )

    timer_summary = timer_commands.add_parser(
        "summary", help="Total time by day, category and task"
    )
    timer_summary.add_argument("--days", type=positive_int, default=7)
    timer_summary.add_argument(
        "--json", action="store_true", help="Print the summary as JSON"
    )

    timer_list = timer_commands.add_parser("list", help="List recorded time entries")
    timer_list.add_argument("--task", dest="task_id", type=positive_int)
    timer_list.add_argument(
        "--days", type=positive_int, default=7,
        help="How many days back to show (default: 7)"
    )

    backup = commands.add_parser("backup", help="Back up and restore the database")
    backup_commands = backup.add_subparsers(dest="backup_command", required=True)

    backup_create = backup_commands.add_parser("create", help="Save a backup now")
    backup_create.add_argument("--label", help="Short name added to the file name")
    backup_create.add_argument(
        "--dir", dest="backup_dir",
        help="Folder for the backup (default: 'backups' next to the database)"
    )

    backup_list = backup_commands.add_parser("list", help="Show saved backups")
    backup_list.add_argument(
        "--dir", dest="backup_dir", help="Folder to look in (default: next to the database)"
    )

    backup_verify = backup_commands.add_parser(
        "verify", help="Check that a backup file is healthy"
    )
    backup_verify.add_argument("file", help="Path of the backup file")

    backup_restore = backup_commands.add_parser(
        "restore", help="Replace the current database with a backup"
    )
    backup_restore.add_argument("file", help="Path of the backup file")
    backup_restore.add_argument(
        "-y", "--yes", action="store_true", help="Restore without asking"
    )

    backup_prune = backup_commands.add_parser(
        "prune", help="Delete old backups, keeping the newest ones"
    )
    backup_prune.add_argument(
        "--keep", type=positive_int, default=5,
        help="How many recent backups to keep (default: 5)"
    )
    backup_prune.add_argument("--dir", dest="backup_dir")
    backup_prune.add_argument(
        "-y", "--yes", action="store_true", help="Delete without asking"
    )

    stats = commands.add_parser("stats", help="Show productivity statistics")
    stats.add_argument(
        "--detailed", action="store_true",
        help="Show the full breakdown with tags, deadlines and insights"
    )
    stats.add_argument(
        "--json", action="store_true",
        help="Print all statistics as JSON"
    )

    complete = commands.add_parser("complete", help="Complete a task")
    complete.add_argument("task_id", type=positive_int)

    show = commands.add_parser("show", help="Show all details of one task")
    show.add_argument("task_id", type=positive_int)

    reopen = commands.add_parser("reopen", help="Move a completed task back to pending")
    reopen.add_argument("task_id", type=positive_int)

    edit = commands.add_parser("edit", help="Change fields of an existing task")
    edit.add_argument("task_id", type=positive_int)
    edit.add_argument("--title")
    edit.add_argument("--description")
    edit.add_argument("--priority", choices=["low", "medium", "high"])
    edit.add_argument("--category")
    repeat = edit.add_mutually_exclusive_group()
    repeat.add_argument("--repeat", choices=RULES, help="Make the task repeat")
    repeat.add_argument(
        "--no-repeat", action="store_true", help="Stop the task repeating"
    )
    due = edit.add_mutually_exclusive_group()
    due.add_argument("--due-date", type=valid_date, help="YYYY-MM-DD")
    due.add_argument(
        "--clear-due-date", action="store_true", help="Remove the due date"
    )

    delete = commands.add_parser("delete", help="Delete a task")
    delete.add_argument("task_id", type=positive_int)
    delete.add_argument(
        "-y", "--yes", action="store_true",
        help="Delete without asking for confirmation"
    )

    report = commands.add_parser("report", help="Export productivity report")
    report.add_argument("--output", default="productivity_report.txt")

    # Journal commands
    journal = commands.add_parser("journal", help="Manage daily journal")
    journal_commands = journal.add_subparsers(
        dest="journal_command",
        required=True
    )

    journal_add = journal_commands.add_parser("add", help="Create journal entry")
    journal_add.add_argument(
        "--date", dest="entry_date", type=valid_date, help="YYYY-MM-DD (default: today)"
    )
    journal_add.add_argument("--achievements", default="")
    journal_add.add_argument("--challenges", default="")
    journal_add.add_argument("--next-steps", default="")

    journal_show = journal_commands.add_parser("show", help="View journal entry")
    journal_show.add_argument("entry_date", type=valid_date)

    journal_list = journal_commands.add_parser("list", help="List journal entries")
    journal_list.add_argument("--limit", type=positive_int, default=7)
    journal_list.add_argument("--search")
    journal_list.add_argument("--from-date", type=valid_date)
    journal_list.add_argument("--to-date", type=valid_date)

    journal_update = journal_commands.add_parser("update", help="Update journal entry")
    journal_update.add_argument("entry_date", type=valid_date)
    journal_update.add_argument("--achievements")
    journal_update.add_argument("--challenges")
    journal_update.add_argument("--next-steps")

    journal_delete = journal_commands.add_parser("delete", help="Delete journal entry")
    journal_delete.add_argument("entry_date", type=valid_date)
    reminders = commands.add_parser(
        "reminders",
        help="Show overdue tasks and upcoming due dates"
    )
    reminders.add_argument(
        "--days",
        type=non_negative_int,
        default=7,
        help="Show tasks due within the next N days"
    )
    return parser


def is_overdue(due_date, today=None):
    """True if the due date is before today. Unreadable dates are not overdue."""
    try:
        return date.fromisoformat(str(due_date)) < (today or date.today())
    except ValueError:
        return False


def format_task_line(task, today=None):
    status = "Done" if task.completed else "Pending"
    line = (
        f"[{task.task_id}] {task.title} | "
        f"{task.priority} | {task.category} | {status}"
    )

    if task.due_date:
        line += f" | due {task.due_date}"

        if not task.completed and is_overdue(task.due_date, today):
            line += " (OVERDUE)"

    if task.recurrence:
        line += f" | repeats {task.recurrence}"

    if task.tags:
        line += " | " + " ".join(f"#{tag}" for tag in task.tags)

    return line


def handle_export(manager, args):
    try:
        tasks = filter_tasks(
            manager.get_all_tasks(),
            priority=args.priority,
            category=args.category,
            status=args.status,
            tags=args.tag
        )
        output = args.output or f"tasks_export.{args.format}"
        time_totals = (
            TimeTracker(manager.database).totals_by_task()
            if args.include_time else None
        )
        path = export_tasks(tasks, output, args.format, time_totals)
    except (ValueError, OSError) as error:
        print(f"Could not export tasks: {error}")
        return

    print(f"Exported {len(tasks)} task(s) to: {path}")


def handle_import(manager, args):
    try:
        result = import_tasks_csv(
            args.csv_file,
            manager,
            dry_run=args.dry_run,
            allow_duplicates=args.allow_duplicates
        )
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print(f"Could not import tasks: {error}")
        return

    prefix = "[Dry run] Would import" if args.dry_run else "Imported"
    print(f"{prefix} {result.imported} task(s).")

    if result.duplicates:
        print(f"Skipped {result.duplicates} duplicate task(s).")

    if result.failed:
        print(f"Skipped {result.failed} invalid row(s):")
        for message in result.errors[:10]:
            print(f"  {message}")
        if len(result.errors) > 10:
            print(f"  ...and {len(result.errors) - 10} more.")


def handle_goal(manager, args):
    tracker = GoalTracker(manager.database)

    try:
        if args.goal_command == "set":
            tracker.set_goal(args.period, args.target)
            print(f"{args.period.title()} goal set to {args.target} task(s).")

        elif args.goal_command == "clear":
            removed = tracker.clear_goal(args.period)
            print(
                f"{args.period.title()} goal removed." if removed
                else f"No {args.period} goal was set."
            )

        else:
            progress = tracker.get_all_progress()

            if not progress:
                print("No goals set. Try: goal set daily 3")
                return

            for item in progress:
                print(format_progress(item))

    except ValueError as error:
        print(error)


def describe_streak(manager):
    """One-line streak status shown after completing a task."""
    length = StreakTracker(manager.database).current_streak()["length"]

    if length <= 1:
        return "Streak: 1 day. Keep it going tomorrow!"

    return f"Streak: {length} days. Keep it going!"


def handle_edit(manager, args):
    changes = {
        "title": args.title,
        "description": args.description,
        "priority": args.priority,
        "category": args.category,
        "due_date": args.due_date,
        "recurrence": args.repeat,
    }
    changes = {key: value for key, value in changes.items() if value is not None}

    if args.no_repeat:
        changes["recurrence"] = None

    if args.clear_due_date:
        changes["due_date"] = None

    if not changes:
        print("Nothing to change. Use --title, --description, --priority, "
              "--category, --due-date, --clear-due-date, --repeat or --no-repeat.")
        return 1

    if "category" in changes and not changes["category"].strip():
        print("Category cannot be empty.")
        return 1

    try:
        task = manager.update_task(args.task_id, **changes)
    except ValueError as error:
        print(f"Could not update task: {error}")
        return 1

    if task is None:
        print("Task not found.")
        return 1

    print(f"Task {task.task_id} updated.")
    print(format_task_line(task))
    return 0


def format_task_details(task, tracked_seconds=0, timer_running=False):
    """Multi-line view of a single task."""
    if task.completed:
        status = f"Completed ({task.completed_at})" if task.completed_at else "Completed"
    else:
        status = "Pending"

    lines = [
        f"Task {task.task_id}: {task.title}",
        f"  Status:      {status}",
        f"  Priority:    {task.priority}",
        f"  Category:    {task.category}",
        f"  Due date:    {task.due_date or 'none'}",
        f"  Repeats:     {task.recurrence or 'no'}",
        f"  Tags:        {' '.join('#' + tag for tag in task.tags) or 'none'}",
        f"  Created:     {task.created_at}",
        f"  Description: {task.description or 'none'}",
    ]

    if tracked_seconds or timer_running:
        tracked = format_duration(tracked_seconds)
        lines.insert(len(lines) - 1, f"  Time spent:  {tracked}" + (" (timer running)" if timer_running else ""))

    return "\n".join(lines)


def handle_show(manager, args):
    task = manager.get_task(args.task_id)

    if task is None:
        print("Task not found.")
        return 1

    tracker = TimeTracker(manager.database)
    running = manager.database.get_running_entry()
    print(format_task_details(
        task,
        tracked_seconds=tracker.total_seconds(task.task_id),
        timer_running=bool(running and running["task_id"] == task.task_id),
    ))
    return 0


def confirm(question):
    """Ask a yes/no question; anything but yes (or no input) means no."""
    try:
        answer = input(f"{question} [y/N]: ")
    except EOFError:
        return False

    return answer.strip().casefold() in {"y", "yes"}


def handle_delete(manager, args):
    task = manager.get_task(args.task_id)

    if task is None:
        print("Task not found.")
        return 1

    if not args.yes and not confirm(
        f"Delete task {task.task_id} '{task.title}'? This cannot be undone."
    ):
        print("Cancelled. Nothing was deleted.")
        return 0

    manager.delete_task(args.task_id)
    print("Task deleted.")
    return 0


def handle_reopen(manager, args):
    task = manager.get_task(args.task_id)

    if task is None:
        print("Task not found.")
        return 1

    if not task.completed:
        print(f"Task {task.task_id} is already pending.")
        return 0

    manager.reopen_task(args.task_id)
    print(f"Task {task.task_id} reopened.")
    return 0


def format_time_entry(entry):
    """One line: '#4 2026-11-10 09:00-09:45 | 45m | task 1: Write docs'."""
    start = entry["started_at"]
    end = entry["ended_at"][11:16] if entry["ended_at"] else "now"
    suffix = " (running)" if not entry["ended_at"] else ""

    return (
        f"#{entry['entry_id']} {start[:10]} {start[11:16]}-{end} | "
        f"{format_duration(entry['seconds'])} | "
        f"task {entry['task_id']}: {entry['title']}{suffix}"
    )


def handle_backup(manager, args):
    db_path = manager.database.db_path

    try:
        if args.backup_command == "create":
            info = create_backup(db_path, args.backup_dir, label=args.label)
            print(f"Backup created: {info['path']}")
            print(
                f"Contents: {format_counts(info['counts'])} "
                f"({format_size(info['size_bytes'])})"
            )
        elif args.backup_command == "list":
            folder = args.backup_dir or default_backup_dir(db_path)
            backups = list_backups(folder)

            if not backups:
                print(f"No backups found in {folder}")
                return 0

            print(f"Backups in {folder} (newest first):")
            for entry in backups:
                print(f"  {format_backup_entry(entry)}")
        elif args.backup_command == "restore":
            problems = verify_database(args.file)
            if problems:
                print(f"Cannot restore {args.file}:")
                for problem in problems:
                    print(f"  - {problem}")
                return 1

            incoming = describe_database(args.file)["counts"]
            current = (
                describe_database(db_path)["counts"]
                if Path(db_path).is_file() else None
            )

            print(f"Backup:  {format_counts(incoming)}")
            print(f"Current: {format_counts(current) if current else 'no database yet'}")
            print("A safety copy of the current database is saved first.")

            if not args.yes and not confirm(
                "Replace the current database with this backup?"
            ):
                print("Cancelled. Nothing was changed.")
                return 0

            result = restore_backup(args.file, db_path)
            print(f"Restored: {format_counts(result['counts'])}")
            if result["safety_backup"]:
                note = "" if result["safety_verified"] else " (current database was damaged; copied as-is)"
                print(f"Previous data saved to: {result['safety_backup']}{note}")

        elif args.backup_command == "prune":
            folder = args.backup_dir or default_backup_dir(db_path)
            doomed = backups_to_prune(folder, args.keep)

            if not doomed:
                print(f"Nothing to delete. {args.keep} or fewer backups in {folder}.")
                return 0

            print(f"Would delete {len(doomed)} old backup(s), keeping the newest {args.keep}:")
            for entry in doomed:
                print(f"  {entry['name']}")

            if not args.yes and not confirm("Delete these backups?"):
                print("Cancelled. Nothing was deleted.")
                return 0

            removed = prune_backups(folder, args.keep)
            print(f"Deleted {len(removed)} backup(s). Safety copies are never deleted.")

        elif args.backup_command == "verify":
            problems = verify_database(args.file)

            if problems:
                print(f"Problems found in {args.file}:")
                for problem in problems:
                    print(f"  - {problem}")
                return 1

            info = describe_database(args.file)
            print(f"OK: {args.file}")
            print(
                f"Contents: {format_counts(info['counts'])} "
                f"({format_size(info['size_bytes'])})"
            )
    except ValueError as error:
        print(f"Backup failed: {error}")
        return 1

    return 0


def handle_timer(manager, args):
    tracker = TimeTracker(manager.database)

    try:
        if args.timer_command == "start":
            entry = tracker.start(args.task_id)
            task = manager.get_task(entry["task_id"])
            print(f"Timer started on task {task.task_id}: {task.title}")

        elif args.timer_command == "stop":
            entry = tracker.stop()
            task = manager.get_task(entry["task_id"])
            total = tracker.total_seconds(entry["task_id"])
            print(
                f"Stopped timer on task {task.task_id}: {task.title}\n"
                f"Time: {format_duration(entry['seconds'])} | "
                f"Total on this task: {format_duration(total)}"
            )

        elif args.timer_command == "log":
            day = date.fromisoformat(args.log_date) if args.log_date else None
            tracker.log_manual(args.task_id, args.duration, day=day)
            task = manager.get_task(args.task_id)
            total = tracker.total_seconds(args.task_id)
            print(
                f"Logged {format_duration(args.duration)} on task "
                f"{task.task_id}: {task.title}\n"
                f"Total on this task: {format_duration(total)}"
            )

        elif args.timer_command == "delete":
            entry = manager.database.get_time_entry(args.entry_id)

            if entry is None:
                print(f"Time entry {args.entry_id} not found.")
                return 1

            if not args.yes and not confirm(
                f"Delete time entry {args.entry_id}? This cannot be undone."
            ):
                print("Cancelled. Nothing was deleted.")
                return 0

            manager.database.delete_time_entry(args.entry_id)
            print(f"Time entry {args.entry_id} deleted.")

        elif args.timer_command == "summary":
            summary = tracker.get_summary(days=args.days)

            if args.json:
                print(json.dumps(summary, indent=2))
            else:
                print(format_time_summary(summary))

        elif args.timer_command == "list":
            entries = tracker.list_entries(args.task_id, args.days)

            if not entries:
                print(f"No time entries in the last {args.days} day(s).")
                return 0

            for entry in entries:
                print(format_time_entry(entry))

        elif args.timer_command == "status":
            status = tracker.status()

            if status is None:
                print("No timer is running.")
                return 0

            print(
                f"Timer running on task {status['task_id']}: {status['title']} "
                f"({format_duration(status['seconds'])})"
            )
            if status["stale"]:
                print(
                    f"Warning: this timer has been running for over "
                    f"{STALE_AFTER_SECONDS // 3600} hours. "
                    "Use 'timer stop' if you forgot it."
                )

    except ValueError as error:
        print(error)
        return 1

    return 0


def handle_streak(manager, args):
    try:
        summary = StreakTracker(manager.database).get_summary(days=args.days)
    except ValueError as error:
        print(error)
        return

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_streak_summary(summary))


def handle_tags(manager, args):
    if args.tag_command == "list":
        counts = manager.get_all_tags()

        if not counts:
            print("No tags found.")
            return

        for name, total in counts.items():
            print(f"#{name} ({total})")
        return

    try:
        tags = parse_tag_string(args.tags)

        if not tags:
            print("Provide at least one tag.")
            return

        if args.tag_command == "add":
            task = manager.add_tags(args.task_id, tags)
        else:
            task = manager.remove_tags(args.task_id, tags)
    except ValueError as error:
        print(error)
        return

    if task is None:
        print("Task not found.")
        return

    shown = " ".join(f"#{tag}" for tag in task.tags) or "none"
    print(f"Tags for task {task.task_id}: {shown}")


def display_journal_entry(entry):
    print(f"\nDate: {entry['entry_date']}")
    print(f"Achievements: {entry['achievements'] or 'None'}")
    print(f"Challenges: {entry['challenges'] or 'None'}")
    print(f"Next steps: {entry['next_steps'] or 'None'}")
    print(f"Last updated: {entry['updated_at']}")


def handle_journal(args):
    db_path = getattr(args, "db", None)
    journal = ProductivityJournal(db_path) if db_path else ProductivityJournal()

    if args.journal_command == "add":
        try:
            entry = journal.add_entry(
                achievements=args.achievements,
                challenges=args.challenges,
                next_steps=args.next_steps,
                entry_date=args.entry_date
            )
            print(f"Journal entry created for {entry['entry_date']}.")
        except (ValueError, sqlite3.IntegrityError) as error:
            print(f"Could not create journal entry: {error}")

    elif args.journal_command == "show":
        entry = journal.get_entry(args.entry_date)

        if entry:
            display_journal_entry(entry)
        else:
            print("Journal entry not found.")

    elif args.journal_command == "list":
        try:
            entries = journal.get_all_entries(
                limit=args.limit,
                keyword=args.search,
                start_date=args.from_date,
                end_date=args.to_date
            )

            if not entries:
                print("No journal entries found.")
                return

            for entry in entries:
                print(
                    f"{entry['entry_date']} | "
                    f"Achievements: {entry['achievements'][:50] or 'None'}"
                )
        except ValueError as error:
            print(error)

    elif args.journal_command == "update":
        try:
            updated = journal.update_entry(
                entry_date=args.entry_date,
                achievements=args.achievements,
                challenges=args.challenges,
                next_steps=args.next_steps
            )
            print("Journal entry updated." if updated else "Journal entry not found.")
        except ValueError as error:
            print(error)

    elif args.journal_command == "delete":
        deleted = journal.delete_entry(args.entry_date)
        print("Journal entry deleted." if deleted else "Journal entry not found.")

def show_reminders(manager, days=7):
    if days < 0:
        print("Days cannot be negative.")
        return

    today = date.today()
    deadline = today + timedelta(days=days)

    overdue = []
    upcoming = []

    for task in manager.get_all_tasks():
        if task.completed or not task.due_date:
            continue

        try:
            due_date = date.fromisoformat(str(task.due_date))
        except ValueError:
            continue

        if due_date < today:
            overdue.append((task, due_date))
        elif due_date <= deadline:
            upcoming.append((task, due_date))

    print("\n=== OVERDUE TASKS ===")

    if overdue:
        for task, due_date in sorted(overdue, key=lambda item: item[1]):
            print(f"[{task.task_id}] {task.title} | Due: {due_date}")
    else:
        print("No overdue tasks.")

    print(f"\n=== DUE WITHIN {days} DAYS ===")

    if upcoming:
        for task, due_date in sorted(upcoming, key=lambda item: item[1]):
            print(f"[{task.task_id}] {task.title} | Due: {due_date}")
    else:
        print("No upcoming tasks.")


def main(argv=None):
    """Run the CLI and return an exit code (0 = success)."""
    try:
        return _run(argv) or 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except sqlite3.Error as error:
        print(f"Database error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"File error: {error}", file=sys.stderr)
        return 1


def _run(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "journal":
        handle_journal(args)
        return

    manager = TaskManager(Database(args.db) if args.db else None)
    if args.command == "reminders":
            show_reminders(manager, args.days)
            return
    

    if args.command == "tag":
        handle_tags(manager, args)
        return

    if args.command == "export":
        handle_export(manager, args)
        return

    if args.command == "import":
        handle_import(manager, args)
        return

    if args.command == "goal":
        handle_goal(manager, args)
        return

    if args.command == "streak":
        handle_streak(manager, args)
        return

    if args.command == "edit":
        return handle_edit(manager, args)

    if args.command == "timer":
        return handle_timer(manager, args)

    if args.command == "backup":
        return handle_backup(manager, args)

    if args.command == "show":
        return handle_show(manager, args)

    if args.command == "delete":
        return handle_delete(manager, args)

    if args.command == "reopen":
        return handle_reopen(manager, args)

    if args.command == "add":
        try:
            task = manager.create_task(
                title=args.title,
                description=args.description,
                priority=args.priority,
                category=args.category,
                due_date=args.due_date,
                tags=parse_tag_string(args.tags),
                recurrence=args.repeat
            )
        except ValueError as error:
            print(f"Could not create task: {error}")
            return
        print(f"Task created successfully. ID: {task.task_id}")

    elif args.command == "list":
        try:
            tasks = filter_tasks(
                manager.get_all_tasks(),
                keyword=args.search,
                priority=args.priority,
                category=args.category,
                status=args.status,
                tags=args.tag,
                sort_by=args.sort,
                descending=not args.ascending
            )
        except ValueError as error:
            print(error)
            return

        if not tasks:
            print("No matching tasks found.")
            return

        for task in tasks:
            print(format_task_line(task))

    elif args.command == "complete":
        stopped = None
        running = manager.database.get_running_entry()
        if running and running["task_id"] == args.task_id:
            stopped = TimeTracker(manager.database).stop()

        done, following = manager.complete_with_recurrence(args.task_id)

        if done:
            print("Task completed.")
            if following:
                print(
                    f"Next occurrence created: [{following.task_id}] "
                    f"{following.title} (due {following.due_date})"
                )
            if stopped:
                print(f"Timer stopped automatically ({format_duration(stopped['seconds'])}).")
            for item in GoalTracker(manager.database).get_all_progress():
                print(format_progress(item))
            print(describe_streak(manager))
        else:
            print("Task not found.")
            return 1

    elif args.command == "stats":
        analytics = ProductivityAnalytics(manager.database)

        if args.json:
            print(json.dumps(
                analytics.get_detailed_stats(), indent=2, ensure_ascii=False
            ))
        elif args.detailed:
            print(ProductivityReports(manager.database).generate_text_report())
        else:
            overview = analytics.get_overview()
            print(f"Total: {overview['total']}")
            print(f"Completed: {overview['completed']}")
            print(f"Pending: {overview['pending']}")
            print(f"Completion rate: {overview['completion_rate']}%")

    elif args.command == "report":
        reports = ProductivityReports(manager.database)
        print(f"Report exported to: {reports.export_report(args.output)}")


if __name__ == "__main__":
    sys.exit(main())