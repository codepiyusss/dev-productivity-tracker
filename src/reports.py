from src.analytics import ProductivityAnalytics
from src.dependencies import DependencyManager
from src.goals import GoalTracker, format_progress
from src.streaks import StreakTracker, format_streak_summary
from src.timetracking import TimeTracker, format_time_summary


class ProductivityReports:
    def __init__(self, database):
        self.analytics = ProductivityAnalytics(database)
        self.goals = GoalTracker(database)
        self.dependencies = DependencyManager(database)
        self.streaks = StreakTracker(database)
        self.time_tracker = TimeTracker(database)

    def generate_text_report(self):
        overview = self.analytics.get_overview()
        priorities = self.analytics.get_priority_breakdown()
        categories = self.analytics.get_category_breakdown()
        overdue = self.analytics.get_overdue_tasks()

        lines = [
            "PRODUCTIVITY REPORT",
            "=" * 35,
            f"Total tasks: {overview['total']}",
            f"Completed: {overview['completed']}",
            f"Pending: {overview['pending']}",
            f"Completion rate: {overview['completion_rate']}%",
            f"Overdue tasks: {len(overdue)}",
            "",
            "PRIORITY BREAKDOWN",
            "-" * 35
        ]

        for priority, count in sorted(priorities.items()):
            lines.append(f"{priority.title()}: {count}")

        lines.extend(["", "CATEGORY BREAKDOWN", "-" * 35])

        for category, count in sorted(categories.items()):
            lines.append(f"{category.title()}: {count}")

        lines.extend(self._detail_sections())

        return "\n".join(lines)

    def _detail_sections(self):
        analytics = self.analytics
        lines = []

        completion = analytics.get_priority_completion()
        if completion:
            lines.extend(["", "COMPLETION BY PRIORITY", "-" * 35])
            for name, data in completion.items():
                lines.append(
                    f"{name.title()}: {data['completed']}/{data['total']} "
                    f"({data['completion_rate']}%)"
                )

        tags = analytics.get_tag_breakdown()
        if tags:
            lines.extend(["", "TAG BREAKDOWN", "-" * 35])
            for name, data in tags.items():
                lines.append(
                    f"#{name}: {data['completed']}/{data['total']} "
                    f"({data['completion_rate']}%)"
                )

        overdue = analytics.get_overdue_tasks()
        if overdue:
            lines.extend(["", "OVERDUE TASKS", "-" * 35])
            for task in overdue:
                lines.append(f"[{task.task_id}] {task.title} (due {task.due_date})")

        due_soon = analytics.get_due_soon_tasks()
        if due_soon:
            lines.extend(["", "DUE IN NEXT 7 DAYS", "-" * 35])
            for task in due_soon:
                lines.append(f"[{task.task_id}] {task.title} (due {task.due_date})")

        blocker_map = self.dependencies.get_blocker_map()
        if blocker_map:
            tasks = {t.task_id: t for t in self.dependencies.get_blocked_tasks()}
            lines.extend(["", "BLOCKED TASKS", "-" * 35])
            for task_id, blocker_ids in blocker_map.items():
                waiting_on = ", ".join(f"#{number}" for number in blocker_ids)
                lines.append(
                    f"[{task_id}] {tasks[task_id].title} (waiting on {waiting_on})"
                )

        goal_progress = self.goals.get_all_progress()
        if goal_progress:
            lines.extend(["", "GOALS", "-" * 35])
            lines.extend(format_progress(item) for item in goal_progress)

        streak_summary = self.streaks.get_summary()
        if streak_summary["total_active_days"]:
            lines.extend(["", "STREAKS", "-" * 35])
            lines.extend(format_streak_summary(streak_summary).splitlines())

        time_summary = self.time_tracker.get_summary(days=7)
        if time_summary["entry_count"]:
            lines.extend(["", "TIME TRACKING", "-" * 35])
            lines.extend(format_time_summary(time_summary).splitlines())

        lines.extend(["", "INSIGHTS", "-" * 35])
        lines.extend(f"- {insight}" for insight in analytics.get_insights())

        return lines

    def export_report(self, output_path="productivity_report.txt"):
        report = self.generate_text_report()

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(report)

        return output_path
