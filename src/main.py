import argparse

from src.tasks import TaskManager
from src.analytics import ProductivityAnalytics
from src.reports import ProductivityReports


def build_parser():
    parser = argparse.ArgumentParser(
        description="Dev Productivity Tracker"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="Create a task")
    add.add_argument("title")
    add.add_argument("--priority", choices=["low", "medium", "high"], default="medium")
    add.add_argument("--category", default="general")
    add.add_argument("--description", default="")
    add.add_argument("--due-date")

    commands.add_parser("list", help="List all tasks")
    commands.add_parser("stats", help="Show productivity statistics")

    complete = commands.add_parser("complete", help="Complete a task")
    complete.add_argument("task_id", type=int)

    delete = commands.add_parser("delete", help="Delete a task")
    delete.add_argument("task_id", type=int)

    report = commands.add_parser("report", help="Export productivity report")
    report.add_argument("--output", default="productivity_report.txt")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    manager = TaskManager()

    if args.command == "add":
        task = manager.create_task(
            title=args.title,
            description=args.description,
            priority=args.priority,
            category=args.category,
            due_date=args.due_date
        )
        print(f"Task created successfully. ID: {task.task_id}")

    elif args.command == "list":
        tasks = manager.get_all_tasks()
        if not tasks:
            print("No tasks found.")
            return

        for task in tasks:
            status = "Done" if task.completed else "Pending"
            print(
                f"[{task.task_id}] {task.title} | "
                f"{task.priority} | {task.category} | {status}"
            )

    elif args.command == "complete":
        if manager.complete_task(args.task_id):
            print("Task completed.")
        else:
            print("Task not found.")

    elif args.command == "delete":
        if manager.delete_task(args.task_id):
            print("Task deleted.")
        else:
            print("Task not found.")

    elif args.command == "stats":
        analytics = ProductivityAnalytics(manager.database)
        print(analytics.get_overview())

    elif args.command == "report":
        reports = ProductivityReports(manager.database)
        path = reports.export_report(args.output)
        print(f"Report exported to: {path}")


if __name__ == "__main__":
    main()
