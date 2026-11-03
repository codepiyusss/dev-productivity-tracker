# Changelog

## Unreleased
- Add task tags: multiple tags per task, add/remove tags, filter by tag, tags shown in listings.
- Add `task_tags` table with automatic, non-destructive migration for existing databases.
- Add `tag add`, `tag remove` and `tag list` CLI commands, plus `--tags` on `add` and `--tag` on `list`.
- Fix outdated `test_task_completion` test (used a method that does not exist).

## 0.1.0
- Initial development.
