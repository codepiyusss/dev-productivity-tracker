import argparse
import sqlite3

from src.tasks import TaskManager
from src.analytics import ProductivityAnalytics
from src.reports import ProductivityReports
from src.task_filters import filter_tasks
from src.journal import ProductivityJournal
from src.utils import parse_tag_string
from datetime import date, timedelta


def build_parser():
    parser = argparse.ArgumentParser(
        description="Dev Productivity Tracker"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    # Task commands
    add = commands.add_parser("add", help="Create a task")
    add.add_argument("title")
    add.add_argument("--priority", choices=["low", "medium", "high"], default="medium")
    add.add_argument("--category", default="general")
    add.add_argument("--description", default="")
    add.add_argument("--due-date")
    add.add_argument("--tags", help="Comma-separated tags, e.g. work,urgent")

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

    # Tag commands
    tag = commands.add_parser("tag", help="Manage task tags")
    tag_commands = tag.add_subparsers(dest="tag_command", required=True)

    tag_add = tag_commands.add_parser("add", help="Add tags to a task")
    tag_add.add_argument("task_id", type=int)
    tag_add.add_argument("tags", help="Comma-separated tags")

    tag_remove = tag_commands.add_parser("remove", help="Remove tags from a task")
    tag_remove.add_argument("task_id", type=int)
    tag_remove.add_argument("tags", help="Comma-separated tags")

    tag_commands.add_parser("list", help="List all tags with task counts")

    commands.add_parser("stats", help="Show productivity statistics")

    complete = commands.add_parser("complete", help="Complete a task")
    complete.add_argument("task_id", type=int)

    delete = commands.add_parser("delete", help="Delete a task")
    delete.add_argument("task_id", type=int)

    report = commands.add_parser("report", help="Export productivity report")
    report.add_argument("--output", default="productivity_report.txt")

    # Journal commands
    journal = commands.add_parser("journal", help="Manage daily journal")
    journal_commands = journal.add_subparsers(
        dest="journal_command",
        required=True
    )

    journal_add = journal_commands.add_parser("add", help="Create journal entry")
    journal_add.add_argument("--date", dest="entry_date")
    journal_add.add_argument("--achievements", default="")
    journal_add.add_argument("--challenges", default="")
    journal_add.add_argument("--next-steps", default="")

    journal_show = journal_commands.add_parser("show", help="View journal entry")
    journal_show.add_argument("entry_date")

    journal_list = journal_commands.add_parser("list", help="List journal entries")
    journal_list.add_argument("--limit", type=int, default=7)
    journal_list.add_argument("--search")
    journal_list.add_argument("--from-date")
    journal_list.add_argument("--to-date")

    journal_update = journal_commands.add_parser("update", help="Update journal entry")
    journal_update.add_argument("entry_date")
    journal_update.add_argument("--achievements")
    journal_update.add_argument("--challenges")
    journal_update.add_argument("--next-steps")

    journal_delete = journal_commands.add_parser("delete", help="Delete journal entry")
    journal_delete.add_argument("entry_date")
    reminders = commands.add_parser(
        "reminders",
        help="Show overdue tasks and upcoming due dates"
    )
    reminders.add_argument(
        "--days",
        type=int,
        default=7,
        help="Show tasks due within the next N days"
    )
    return parser


def format_task_line(task):
    status = "Done" if task.completed else "Pending"
    line = (
        f"[{task.task_id}] {task.title} | "
        f"{task.priority} | {task.category} | {status}"
    )

    if task.tags:
        line += " | " + " ".join(f"#{tag}" for tag in task.tags)

    return line


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
    journal = ProductivityJournal()

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


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "journal":
        handle_journal(args)
        return

    manager = TaskManager()
    if args.command == "reminders":
            show_reminders(manager, args.days)
            return
    

    if args.command == "tag":
        handle_tags(manager, args)
        return

    if args.command == "add":
        try:
            task = manager.create_task(
                title=args.title,
                description=args.description,
                priority=args.priority,
                category=args.category,
                due_date=args.due_date,
                tags=parse_tag_string(args.tags)
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
        print(
            "Task completed." if manager.complete_task(args.task_id)
            else "Task not found."
        )

    elif args.command == "delete":
        print(
            "Task deleted." if manager.delete_task(args.task_id)
            else "Task not found."
        )

    elif args.command == "stats":
        analytics = ProductivityAnalytics(manager.database)
        print(analytics.get_overview())

    elif args.command == "report":
        reports = ProductivityReports(manager.database)
        print(f"Report exported to: {reports.export_report(args.output)}")


if __name__ == "__main__":
    main()