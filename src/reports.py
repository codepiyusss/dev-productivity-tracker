from src.analytics import ProductivityAnalytics


class ProductivityReports:
    def __init__(self, database):
        self.analytics = ProductivityAnalytics(database)

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

        return "\n".join(lines)

    def export_report(self, output_path="productivity_report.txt"):
        report = self.generate_text_report()

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(report)

        return output_path
