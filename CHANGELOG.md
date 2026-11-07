# Changelog

## Unreleased
- Add daily and weekly goals: `goal set`, `goal show` and `goal clear`, with progress bars.
- Show goal progress after `complete` and in the detailed report.
- Track when tasks are completed (`completed_at`), with a safe migration for existing databases. Tasks completed before this version have no timestamp and do not count toward goals.
- Add `completed_at` to CSV and JSON exports.
- Improve analytics: completion rate by priority, category and tag, due-soon and overdue lists, pending task age, weekday patterns and plain-language insights.
- Add `stats --detailed` and `stats --json`; reports now include the new sections.
- Overdue detection no longer crashes on invalid due dates.
- Add `import` command to load tasks from CSV with validation, line-numbered row errors, duplicate skipping and `--dry-run`.
- Add `export` command to save tasks as CSV or JSON, with status, priority, category and tag filters.
- Add `src/exporter.py` with UTF-8, properly escaped CSV output and tags included.
- Add task tags: multiple tags per task, add/remove tags, filter by tag, tags shown in listings.
- Add `task_tags` table with automatic, non-destructive migration for existing databases.
- Add `tag add`, `tag remove` and `tag list` CLI commands, plus `--tags` on `add` and `--tag` on `list`.
- Fix outdated `test_task_completion` test (used a method that does not exist).

## 0.1.0
- Initial development.
